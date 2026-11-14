"""Mixx by YAS: money in from clients, money out to workers.

    python manage.py test tests.test_yas_payments

Nothing in here touches YAS. The outbound calls are stubbed, because
their gateway is live - a test that reached it would move real money,
which is a lesson the other platform paid for once already.

What these are actually checking, in order of how much it would cost to
get wrong:

  a callback cannot be forged. An open endpoint that marks bookings
  paid is free work, and X-Forwarded-For is attacker-controlled;

  a payment is never credited twice, and a repeated callback is quiet;

  a short payment is refused and the booking stays unpaid;

  settling runs the client's assign choice, so a paid job gets workers;

  a payout whose outcome is unknown lands on 'held' and nothing retries
  it, because the money may already have gone.
"""
import base64
import json
from decimal import Decimal as D
from unittest import mock

from django.test import override_settings
from django.utils import timezone

from clients.models import ClientRefund, PaymentTransaction
from jobs.service_request_models import ServiceRequest
from worker_connect import yas, yas_client
from workers.models import MobileMoneyAccount, WorkerPayout

from .test_full_flows import FlowBase, patch_json, post_json

PUSH = '/api/v1/payments/yas/ussd-push/callback/'
W2A = '/api/v1/payments/yas/w2a/'
STATUS = '/api/v1/payments/yas/status/'

SECRET = 'a-shared-secret-only-yas-knows'
THEIR_IP = '41.222.176.233'

# Enough configuration to identify them, with nothing switched on.
IDENTIFIED = dict(YAS_CALLBACK_SECRET=SECRET, YAS_ALLOWED_IPS='',
                  YAS_BILLER_USERNAME='', YAS_BILLER_PASSWORD='',
                  YAS_BILLER_CODE='', YAS_AMOUNT_TOLERANCE='0')

# Everything a client payment needs, switched on.
PAYMENTS_ON = dict(IDENTIFIED,
                   YAS_CLIENT_PAYMENTS_ENABLED=True,
                   YAS_TOKEN_URL='https://gw.example/token',
                   YAS_PAY_URL='https://gw.example/pay',
                   YAS_BILLER_MSISDN='255691511330',
                   YAS_BILLER_USERNAME='wc-partner-login',
                   YAS_BILLER_PASSWORD='secret-password')

# Everything a payout needs, switched on.
PAYOUTS_ON = dict(YAS_WORKER_PAYOUTS_ENABLED=True,
                  YAS_PAYOUT_URL='https://gw.example/a2w',
                  YAS_DISBURSEMENT_MSISDN='255691511330',
                  YAS_DISBURSEMENT_PIN='1456',
                  YAS_BRAND_ID='1232',
                  YAS_SENDER_NAME='Worker Search',
                  YAS_PAYOUT_AUTH='')


# Everything a refund needs, switched on. It carries the Debit Mandate
# token, so the payment settings have to be here too.
REFUNDS_ON = dict(PAYMENTS_ON,
                  YAS_REFUNDS_ENABLED=True,
                  YAS_REFUND_URL='https://gw.example/reverse',
                  YAS_CHANNEL_MSISDN='255691511330',
                  YAS_CHANNEL_PIN='1234')


def xml(root_tags):
    inner = "".join("<%s>%s</%s>" % (k, v, k) for k, v in root_tags)
    return '<?xml version="1.0"?><COMMAND>%s</COMMAND>' % inner


def resmfici(txn_status, txnid='42326232', message='Success'):
    return xml((("TYPE", "RESMFICI"), ("REFERENCEID", "CI0001"),
                ("TXNID", txnid), ("TXNSTATUS", txn_status),
                ("MESSAGE", message)))


def approver():
    """A second superuser, so the one sending is not the one who approved."""
    from accounts.models import User
    user, _ = User.objects.get_or_create(
        username='approver', defaults=dict(
            email='approver@t.co', user_type='admin', is_staff=True,
            is_superuser=True))
    return user


def completed_job(case, wp=None, pay=D('25000')):
    """A booking this worker has completed, earning ``pay`` on it."""
    from jobs.service_request_models import ServiceRequestAssignment
    sr, _ = case.book()
    # A payout needs the client to have paid for the job.
    ServiceRequest.objects.filter(pk=sr.pk).update(payment_status='paid')
    sr.refresh_from_db()
    ServiceRequestAssignment.objects.create(
        service_request=sr, worker=wp or case.wp, status='completed',
        worker_payment=pay)
    return sr


def make_payout(case, amount, wp=None, created_by='approver', **kw):
    """A payout for a job the worker really completed, approved by approver()."""
    wp = wp or case.wp
    if created_by == 'approver':
        created_by = approver()
    # A payout needs a verified wallet to go to by default.
    if not kw.get('phone_number') and not MobileMoneyAccount.objects.filter(
            user=wp.user, provider='tigo_pesa', is_verified=True).exists():
        MobileMoneyAccount.objects.create(
            user=wp.user, provider='tigo_pesa',
            phone_number=wp.user.phone_number or '0714123456',
            account_name='Verified', is_default=True, is_verified=True)
    sr = kw.pop('service_request', None) or completed_job(
        case, wp=wp, pay=max(D(str(amount)), D('25000')))
    return yas_client.create_payout(wp, amount, created_by=created_by,
                                    service_request=sr, **kw)


def make_refund(case, amount, phone, created_by='approver', **kw):
    """A refund against real YAS money on case.sr, approved by approver()."""
    if created_by == 'approver':
        created_by = approver()
    if not yas_client.gateway_payments(case.sr).exists():
        yas.settle(case.sr, '26797615656', amount=case.sr.total_price,
                   gateway_reference=case.ref, payer_msisdn='255714123456')
        case.sr.refresh_from_db()
    return yas_client.create_refund(case.sr, amount, phone,
                                    created_by=created_by, **kw)


class YasBase(FlowBase):
    """A booking with a reference, ready to be paid."""

    def setUp(self):
        super().setUp()
        self.sr, _ref = self.book()
        # book() pays it with a demo reference and an admin has not
        # verified it, so it starts unpaid - which is the state a real
        # YAS payment arrives into.
        self.sr.payment_status = 'pending'
        self.sr.payment_verified = False
        self.sr.paid_at = None
        self.sr.save()
        # book() pays with a demo reference, and PaymentTransaction's
        # consumed_by is a OneToOne - leaving that row here would block
        # the audit row a real payment writes. A booking YAS pays has no
        # demo row, so this makes the starting state the real one.
        PaymentTransaction.objects.filter(consumed_by=self.sr).delete()
        self.ref = self.sr.ensure_reference()

    def push(self, body, secret=SECRET, method='post', **extra):
        headers = {}
        if secret is not None:
            headers['HTTP_X_YAS_SECRET'] = secret
        headers.update(extra)
        if method == 'get':
            return self.client.get(PUSH, body, **headers)
        return post_json(self.client, PUSH, body, **headers)

    def w2a(self, body, secret=SECRET, **extra):
        headers = {}
        if secret is not None:
            headers['HTTP_X_YAS_SECRET'] = secret
        headers.update(extra)
        return self.client.post(W2A, body, content_type='text/xml', **headers)

    def tags(self, response):
        return yas.read_command(response.content) or {}


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------

class ReferenceTests(YasBase):
    def test_a_reference_is_wc_and_eight_characters(self):
        self.assertRegex(self.ref, r'^WC[A-Z0-9]{8}$')

    def test_minting_twice_keeps_the_first_one(self):
        again = self.sr.ensure_reference()
        self.assertEqual(again, self.ref)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.reference, self.ref)

    def test_references_do_not_repeat(self):
        seen = {ServiceRequest.new_reference() for _ in range(200)}
        self.assertEqual(len(seen), 200)

    def test_knowing_the_row_id_does_not_let_you_pay_for_the_job(self):
        # The whole reason this field exists: paying for somebody else's
        # job must not be a matter of typing 48 instead of 47. So an id
        # dressed up as a reference resolves to nothing.
        #
        # Not "the id's digits are absent from the reference" - eight
        # random characters will sometimes contain them, which made that
        # version of this test fail by luck rather than by fault.
        for guess in (str(self.sr.id),
                      'WC' + str(self.sr.id),
                      'WC' + str(self.sr.id).zfill(8),
                      'WC' + str(self.sr.id + 1).zfill(8)):
            self.assertIsNone(yas.request_for(guess), 'on %r' % guess)

    def test_the_reference_of_one_booking_is_not_the_next_ones(self):
        other, _ = self.book()
        self.assertNotEqual(other.ensure_reference(), self.ref)

    def test_our_reference_is_found_with_no_prefix(self):
        self.assertEqual(yas.request_ref_from(self.ref), self.ref)

    @override_settings(YAS_BILLER_CODE='WCX')
    def test_a_configured_prefix_comes_off(self):
        self.assertEqual(yas.request_ref_from('WCX' + self.ref), self.ref)

    def test_a_prefix_we_do_not_know_still_resolves(self):
        # EasyFix has no biller code yet, so this is the case that will
        # actually happen on the first real payment.
        for arrived in ('EASYFIX-' + self.ref, 'XYZ_' + self.ref,
                        '0098' + self.ref, self.ref + '-01'):
            self.assertEqual(yas.request_ref_from(arrived), self.ref,
                             'failed on %r' % arrived)

    def test_lower_case_resolves(self):
        self.assertEqual(yas.request_ref_from(self.ref.lower()), self.ref)

    def test_nothing_resolves_to_nothing(self):
        self.assertEqual(yas.request_ref_from(''), '')
        self.assertEqual(yas.request_ref_from(None), '')
        self.assertIsNone(yas.request_for(''))

    def test_the_request_is_found_by_its_reference(self):
        self.assertEqual(yas.request_for(self.ref).pk, self.sr.pk)
        self.assertIsNone(yas.request_for('WCZZZZZZZZ'))


# ---------------------------------------------------------------------------
# Amounts
# ---------------------------------------------------------------------------

class AmountTests(YasBase):
    def test_shillings_are_whole_and_rounded_down(self):
        self.sr.total_price = D('750.90')
        self.assertEqual(yas.shillings_due(self.sr), D('750'))

    def test_no_price_is_zero_not_a_crash(self):
        self.sr.total_price = None
        self.assertEqual(yas.shillings_due(self.sr), D('0'))

    @override_settings(YAS_AMOUNT_TOLERANCE='0')
    def test_the_exact_amount_covers_it(self):
        self.sr.total_price = D('30000')
        self.assertLessEqual(yas.amount_shortfall(self.sr, D('30000')), 0)
        self.assertGreater(yas.amount_shortfall(self.sr, D('29999')), 0)

    @override_settings(YAS_AMOUNT_TOLERANCE='nonsense')
    def test_a_broken_tolerance_falls_back_to_exact(self):
        # A typo in the environment must not quietly accept half payments.
        self.sr.total_price = D('30000')
        self.assertGreater(yas.amount_shortfall(self.sr, D('15000')), 0)


# ---------------------------------------------------------------------------
# Settling
# ---------------------------------------------------------------------------

class SettleTests(YasBase):
    def test_settling_marks_it_paid(self):
        self.assertTrue(self.sr.mark_paid_by_gateway('26797615656'))
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')
        self.assertTrue(self.sr.payment_verified)
        self.assertIsNotNone(self.sr.paid_at)
        self.assertIsNotNone(self.sr.payment_verified_at)
        self.assertEqual(self.sr.payment_transaction_id, '26797615656')
        self.assertEqual(self.sr.payment_method, 'Mixx by Yas')

    def test_no_admin_is_credited_for_a_gateway_payment(self):
        # Recording an admin who did nothing would be a lie in the audit
        # trail, and payment_verified_by is nullable so there is no need.
        self.sr.mark_paid_by_gateway('26797615656')
        self.sr.refresh_from_db()
        self.assertIsNone(self.sr.payment_verified_by)

    def test_settling_runs_the_clients_assign_choice(self):
        # Without this a paid job sits with nobody assigned while the
        # client waits for workers who were never asked.
        with mock.patch('clients.assignment_mode.apply_assignment_mode') as m:
            self.sr.mark_paid_by_gateway('26797615656')
        m.assert_called_once()
        self.assertEqual(m.call_args[0][0].pk, self.sr.pk)

    def test_settling_twice_does_nothing_the_second_time(self):
        self.assertTrue(self.sr.mark_paid_by_gateway('first'))
        with mock.patch('clients.assignment_mode.apply_assignment_mode') as m:
            self.assertFalse(self.sr.mark_paid_by_gateway('second'))
        m.assert_not_called()
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_transaction_id, 'first')

    def test_a_transaction_row_is_left_behind(self):
        yas.settle(self.sr, '26830652898', amount=D('30000'))
        txn = PaymentTransaction.objects.get(reference='26830652898')
        self.assertFalse(txn.is_demo)
        self.assertEqual(txn.method, 'yas')
        self.assertEqual(txn.consumed_by_id, self.sr.pk)
        self.assertEqual(txn.client_id, self.sr.client_id)

    def test_a_request_that_already_has_a_reference_row_still_settles(self):
        # consumed_by is a OneToOne, so a demo reference already
        # attached to this request blocks the audit row. The payment
        # itself must still go through - the money has left the client.
        PaymentTransaction.objects.create(
            reference='DEMO-YAS-ALREADYHERE', client=self.sr.client,
            amount=D('30000'), method='yas', consumed_by=self.sr,
            consumed_at=timezone.now())
        self.assertTrue(yas.settle(self.sr, '26142805610'))
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')


# ---------------------------------------------------------------------------
# Who may call the callbacks
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class CallerTests(YasBase):
    @override_settings(YAS_CALLBACK_SECRET='', YAS_ALLOWED_IPS='',
                       YAS_BILLER_USERNAME='', YAS_BILLER_PASSWORD='')
    def test_with_nothing_configured_everything_is_refused(self):
        # Not "allow everything until it is set up". An open endpoint
        # that marks bookings paid is free work.
        r = self.push({'ReferenceID': self.ref, 'Status': 'true'},
                      secret=None)
        self.assertEqual(r.status_code, 401)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_the_wrong_secret_is_refused(self):
        r = self.push({'ReferenceID': self.ref, 'Status': 'true'},
                      secret='not-the-secret')
        self.assertEqual(r.status_code, 401)

    def test_no_secret_at_all_is_refused(self):
        self.assertEqual(
            self.push({'ReferenceID': self.ref}, secret=None).status_code, 401)

    def test_the_right_secret_gets_in(self):
        self.assertEqual(
            self.push({'ReferenceID': self.ref, 'Status': 'true'}).status_code,
            200)

    @override_settings(YAS_CALLBACK_SECRET='',
                       YAS_BILLER_USERNAME='wc-partner-login',
                       YAS_BILLER_PASSWORD='secret-password')
    def test_their_username_and_password_get_in(self):
        # They issued these and never said which way round they are
        # used. If they authenticate with them and we only look for our
        # own header, every real payment is refused.
        token = base64.b64encode(b'wc-partner-login:secret-password').decode()
        r = self.push({'ReferenceID': self.ref, 'Status': 'true'},
                      secret=None, HTTP_AUTHORIZATION='Basic ' + token)
        self.assertEqual(r.status_code, 200)

    @override_settings(YAS_CALLBACK_SECRET='',
                       YAS_BILLER_USERNAME='wc-partner-login',
                       YAS_BILLER_PASSWORD='secret-password')
    def test_the_wrong_password_does_not(self):
        token = base64.b64encode(b'wc-partner-login:guessed').decode()
        r = self.push({'ReferenceID': self.ref}, secret=None,
                      HTTP_AUTHORIZATION='Basic ' + token)
        self.assertEqual(r.status_code, 401)

    @override_settings(YAS_CALLBACK_SECRET='',
                       YAS_BILLER_USERNAME='wc-partner-login',
                       YAS_BILLER_PASSWORD='secret-password')
    def test_rubbish_in_the_basic_header_does_not_crash(self):
        for header in ('Basic', 'Basic !!!!', 'Basic ' + base64.b64encode(
                b'\xff\xfe').decode(), 'Bearer abc', ''):
            r = self.push({'ReferenceID': self.ref}, secret=None,
                          HTTP_AUTHORIZATION=header)
            self.assertEqual(r.status_code, 401, 'on %r' % header)

    @override_settings(YAS_CALLBACK_SECRET='', YAS_ALLOWED_IPS=THEIR_IP)
    def test_their_gateway_address_gets_in(self):
        # Their biller callback carries no credential at all, so where
        # it came from is the only thing that can vouch for it.
        r = self.push({'ReferenceID': self.ref, 'Status': 'true'},
                      secret=None, HTTP_X_REAL_IP=THEIR_IP)
        self.assertEqual(r.status_code, 200)

    @override_settings(YAS_CALLBACK_SECRET='', YAS_ALLOWED_IPS=THEIR_IP)
    def test_a_forged_forwarded_for_does_not_get_in(self):
        # nginx builds X-Forwarded-For with $proxy_add_x_forwarded_for,
        # which APPENDS to whatever arrived - so a caller can put their
        # address at the front of it. Only the last entry is ours.
        r = self.push({'ReferenceID': self.ref, 'Status': 'true'},
                      secret=None,
                      HTTP_X_FORWARDED_FOR='%s, 203.0.113.9' % THEIR_IP)
        self.assertEqual(r.status_code, 401)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    @override_settings(YAS_CALLBACK_SECRET='', YAS_ALLOWED_IPS=THEIR_IP)
    def test_x_real_ip_beats_a_forged_chain(self):
        r = self.push({'ReferenceID': self.ref, 'Status': 'true'},
                      secret=None, HTTP_X_REAL_IP=THEIR_IP,
                      HTTP_X_FORWARDED_FOR='203.0.113.9, 198.51.100.4')
        self.assertEqual(r.status_code, 200)

    @override_settings(YAS_CALLBACK_SECRET='', YAS_ALLOWED_IPS=THEIR_IP)
    def test_somebody_elses_address_is_refused(self):
        r = self.push({'ReferenceID': self.ref}, secret=None,
                      HTTP_X_REAL_IP='203.0.113.9')
        self.assertEqual(r.status_code, 401)

    def test_the_secret_is_never_written_to_the_log(self):
        with self.assertLogs('worker_connect.yas', level='INFO') as caught:
            self.push({'ReferenceID': self.ref, 'Status': 'false'})
        self.assertNotIn(SECRET, '\n'.join(caught.output))


# ---------------------------------------------------------------------------
# The USSD push callback
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class UssdPushTests(YasBase):
    def test_a_success_with_the_exact_amount_pays_the_booking(self):
        r = self.push({'ReferenceID': self.ref, 'Status': 'true',
                       'Amount': int(self.sr.total_price),
                       'MFSTransactionID': '26797615656'})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIs(body['ResponseStatus'], True)
        self.assertEqual(body['ResponseCode'], 'BILLER-30-0000-S')
        self.assertEqual(body['ReferenceID'], self.ref)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')
        self.assertEqual(self.sr.payment_transaction_id, '26797615656')

    def test_a_get_works_as_well_as_a_post(self):
        # Their sample says "Request Method: GET" with a JSON body,
        # while every other call in the document is a POST. A callback
        # that arrives by the method we did not allow is a 405.
        r = self.push({'ReferenceID': self.ref, 'Status': 'true',
                       'Amount': int(self.sr.total_price),
                       'MFSTransactionID': '268'}, method='get')
        self.assertEqual(r.status_code, 200)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')

    def test_every_word_they_use_for_success_is_understood(self):
        for word in ('true', 'TRUE', 'Success', 'successful', 'completed',
                     'OK', '0', '200'):
            sr, _ = self.book()
            sr.payment_status = 'pending'
            sr.payment_verified = False
            sr.save()
            ref = sr.ensure_reference()
            self.push({'ReferenceID': ref, 'Status': word,
                       'Amount': int(sr.total_price),
                       'MFSTransactionID': 'x-' + word})
            sr.refresh_from_db()
            self.assertEqual(sr.payment_status, 'paid', 'on %r' % word)

    def test_a_failure_leaves_it_unpaid(self):
        r = self.push({'ReferenceID': self.ref, 'Status': 'failed',
                       'MFSTransactionID': '1'})
        self.assertEqual(r.status_code, 200)
        # Their payment failed; our handling of the news did not, so
        # they are told the callback was accepted and stop retrying.
        self.assertIs(r.json()['ResponseStatus'], True)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_the_same_callback_twice_pays_once(self):
        body = {'ReferenceID': self.ref, 'Status': 'true',
                'Amount': int(self.sr.total_price),
                'MFSTransactionID': '26797615656'}
        self.push(body)
        with mock.patch('clients.assignment_mode.apply_assignment_mode') as m:
            second = self.push(body)
        self.assertEqual(second.status_code, 200)
        m.assert_not_called()
        # One audit row, not two, and the first receipt is the one kept.
        self.assertEqual(PaymentTransaction.objects.filter(
            consumed_by=self.sr).count(), 1)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_transaction_id, '26797615656')

    def test_an_unknown_reference_is_answered_as_handled(self):
        # A failure makes their platform retry for hours, and no amount
        # of retrying will conjure a booking that does not exist.
        r = self.push({'ReferenceID': 'WCNOSUCH01', 'Status': 'true'})
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.json()['ResponseStatus'], True)
        self.assertIn('not recognised', r.json()['ResponseDescription'])

    def test_a_get_with_the_fields_in_the_query_string_works(self):
        # An empty body with a JSON content-type makes DRF raise, and
        # that raise used to become a 400 before the query string was
        # ever read.
        r = self.client.get(
            PUSH + '?ReferenceID=%s&Status=true&MFSTransactionID=77'
            '&Amount=%s' % (self.ref, int(self.sr.total_price)),
            HTTP_X_YAS_SECRET=SECRET, CONTENT_TYPE='application/json')
        self.assertEqual(r.status_code, 200)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')

    def test_a_callback_with_no_reference_does_not_crash(self):
        r = self.push({'Status': 'true'})
        self.assertEqual(r.status_code, 200)

    def test_their_other_spellings_of_the_fields_are_read(self):
        r = self.push({'referenceId': self.ref, 'status': 'true',
                       'amount': int(self.sr.total_price),
                       'mfsTransactionId': '99'})
        self.assertEqual(r.status_code, 200)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')

    def test_the_amount_they_deducted_is_checked(self):
        # Amount is mandatory on their callback and is what actually left
        # the client's wallet (spec p.13). Not reading it is the fault
        # still open on the other platform.
        r = self.push({'ReferenceID': self.ref, 'Status': 'true',
                       'Amount': 1000, 'MFSTransactionID': '26797615656'})
        self.assertEqual(r.status_code, 200)
        # Answered as handled - retrying will not change the amount -
        # but the booking is not paid.
        self.assertIs(r.json()['ResponseStatus'], True)
        self.assertIn('does not match', r.json()['ResponseDescription'])
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_a_short_push_is_shouted_about_not_swallowed(self):
        with self.assertLogs('worker_connect.yas', level='CRITICAL') as caught:
            self.push({'ReferenceID': self.ref, 'Status': 'true',
                       'Amount': 1000, 'MFSTransactionID': '2679'})
        shouted = chr(10).join(caught.output)
        self.assertIn(self.ref, shouted)
        self.assertIn('by hand', shouted)

    def test_the_right_amount_pays_the_booking(self):
        r = self.push({'ReferenceID': self.ref, 'Status': 'true',
                       'Amount': int(self.sr.total_price),
                       'MFSTransactionID': '26797615656'})
        self.assertIs(r.json()['ResponseStatus'], True)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')

    def test_paying_more_is_not_applied_but_recorded(self):
        # Exact in both directions: money above the price is money owed
        # back, so it is recorded for a refund rather than kept.
        with self.assertLogs('worker_connect.yas', level='CRITICAL'):
            self.push({'ReferenceID': self.ref, 'Status': 'true',
                       'Amount': int(self.sr.total_price) + 1000,
                       'MFSTransactionID': 'OVER1'})
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')
        row = PaymentTransaction.objects.get(reference='OVER1')
        self.assertTrue(row.unapplied_reason)
        self.assertEqual(row.service_request_id, self.sr.pk)
        self.assertIsNone(row.consumed_by_id)

    def test_a_missing_amount_does_not_settle_but_is_recorded(self):
        # Their Amount is mandatory and is what left the wallet. Without
        # it we cannot know the booking is covered.
        with self.assertLogs('worker_connect.yas', level='CRITICAL'):
            self.push({'ReferenceID': self.ref, 'Status': 'true',
                       'MFSTransactionID': 'NOAMT1'})
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')
        row = PaymentTransaction.objects.get(reference='NOAMT1')
        self.assertIn('Amount missing', row.unapplied_reason)

    def test_an_unreadable_amount_does_not_settle(self):
        for i, amount in enumerate(('', 'abc', 'NaN', '1e999999', '-5', '0',
                                    'Infinity', [1], {'a': 1})):
            sr, _ = self.book()
            sr.payment_status = 'pending'
            sr.save(update_fields=['payment_status'])
            ref = sr.ensure_reference()
            with self.assertLogs('worker_connect.yas', level='CRITICAL'):
                self.push({'ReferenceID': ref, 'Status': 'true',
                           'Amount': amount, 'MFSTransactionID': 'U%d' % i})
            sr.refresh_from_db()
            self.assertEqual(sr.payment_status, 'pending', 'on %r' % amount)
            # Recorded, so it can be refunded.
            self.assertTrue(PaymentTransaction.objects.filter(
                reference='U%d' % i, service_request=sr).exclude(
                unapplied_reason='').exists(), 'on %r' % amount)

    @override_settings(YAS_CALLBACK_SUCCESS_CODE='BILLER-18-0000-S')
    def test_the_success_code_can_be_changed_without_a_deploy(self):
        # The specification prints it twice with different values, so
        # only the first real test settles which one they want.
        r = self.push({'ReferenceID': self.ref, 'Status': 'true'})
        self.assertEqual(r.json()['ResponseCode'], 'BILLER-18-0000-S')


# ---------------------------------------------------------------------------
# W2A: a client paying from the Mixx menu
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class BillPaymentTests(YasBase):
    def body(self, reference=None, amount=None, txnid='BP140218.1240.B01530'):
        return xml((("TYPE", "SYNC_BILLPAY_REQUEST"), ("TXNID", txnid),
                    ("MSISDN", "0714405395"),
                    ("AMOUNT", str(self.sr.total_price if amount is None
                                   else amount)),
                    ("COMPANYNAME", "12345"),
                    ("CUSTOMERREFERENCEID",
                     self.ref if reference is None else reference),
                    ("SENDERNAME", "James Kaparata")))

    def test_the_right_amount_pays_the_booking(self):
        r = self.w2a(self.body(amount=int(self.sr.total_price)))
        self.assertEqual(r.status_code, 200)
        tags = self.tags(r)
        self.assertEqual(tags['RESULT'], 'TS')
        self.assertEqual(tags['ERRORCODE'], yas.OK)
        self.assertEqual(tags['FLAG'], 'Y')
        self.assertEqual(tags['REFID'], self.ref)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')

    def test_the_reply_is_xml_not_json(self):
        # A DRF renderer would wrap this in JSON quotes and hand YAS a
        # string where their parser wants a document.
        r = self.w2a(self.body())
        self.assertIn('xml', r['Content-Type'])
        self.assertTrue(r.content.lstrip().startswith(b'<?xml'))
        self.assertIn(b'<TYPE>SYNC_BILLPAY_RESPONSE</TYPE>', r.content)

    def test_the_payers_transaction_id_is_echoed_back(self):
        r = self.w2a(self.body(txnid='BP999.1.X'))
        self.assertEqual(self.tags(r)['TXNID'], 'BP999.1.X')

    def test_an_unauthenticated_caller_is_refused(self):
        r = self.w2a(self.body(), secret=None)
        self.assertEqual(r.status_code, 401)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_an_unknown_reference_is_error010(self):
        r = self.w2a(self.body(reference='WCNOSUCH01'))
        tags = self.tags(r)
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(tags['ERRORCODE'], yas.E_REF)
        self.assertEqual(tags['FLAG'], 'N')

    def test_a_short_payment_is_refused_and_nothing_is_paid(self):
        r = self.w2a(self.body(amount=1000))
        tags = self.tags(r)
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(tags['ERRORCODE'], yas.E_TOO_LOW)
        # The reason is shown on the payer's own handset, so it says
        # what to do rather than printing an error number.
        self.assertIn(str(yas.shillings_due(self.sr)), tags['CONTENT'])
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_one_shilling_short_is_still_short(self):
        r = self.w2a(self.body(amount=int(self.sr.total_price) - 1))
        self.assertEqual(self.tags(r)['ERRORCODE'], yas.E_TOO_LOW)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_paying_more_than_due_is_refused(self):
        # Exact in both directions: TF, so YAS do not take the money.
        r = self.w2a(self.body(amount=int(self.sr.total_price) + 5000))
        tags = self.tags(r)
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(tags['ERRORCODE'], yas.E_TOO_HIGH)
        self.assertIn(str(yas.shillings_due(self.sr)), tags['CONTENT'])
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_a_price_with_cents_is_settled_by_the_whole_shillings(self):
        # YAS cannot send forty cents, so a booking priced at 750.40 is
        # settled by 750 rather than refused forever.
        self.sr.total_price = D('30000.40')
        self.sr.save(update_fields=['total_price'])
        r = self.w2a(self.body(amount=30000))
        self.assertEqual(self.tags(r)['RESULT'], 'TS')

    def test_a_nonsense_amount_is_error012(self):
        for amount in ('abc', '', 'NaN', 'Infinity'):
            r = self.w2a(self.body(amount=amount))
            self.assertEqual(self.tags(r)['ERRORCODE'], yas.E_AMOUNT,
                             'on %r' % amount)

    def test_zero_and_negative_are_error012(self):
        for amount in ('0', '-5000'):
            r = self.w2a(self.body(amount=amount))
            self.assertEqual(self.tags(r)['ERRORCODE'], yas.E_AMOUNT,
                             'on %r' % amount)

    def test_an_already_paid_booking_refuses_a_new_payment(self):
        # TS here takes the client's money a second time. Only a genuine
        # retry of the payment that paid it is answered TS.
        self.sr.mark_paid_by_gateway('earlier')
        r = self.w2a(self.body())
        tags = self.tags(r)
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(tags['ERRORCODE'], yas.E_LOCKED)
        self.assertIn('already paid', tags['CONTENT'])
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_transaction_id, 'earlier')

    def test_a_retry_of_the_payment_that_paid_it_answers_success(self):
        self.assertEqual(self.tags(self.w2a(self.body(txnid='BP1')))['RESULT'],
                         'TS')
        tags = self.tags(self.w2a(self.body(txnid='BP1')))
        self.assertEqual(tags['RESULT'], 'TS')
        self.assertIn('already paid', tags['CONTENT'])

    def test_a_refunded_booking_cannot_be_paid(self):
        self.sr.payment_status = 'refunded'
        self.sr.save(update_fields=['payment_status'])
        tags = self.tags(self.w2a(self.body()))
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(tags['ERRORCODE'], yas.E_LOCKED)

    def test_a_failed_payment_can_still_be_paid(self):
        # A mistyped PIN is the commonest reason for a failure, and the
        # client's next attempt should work.
        self.sr.payment_status = 'failed'
        self.sr.save(update_fields=['payment_status'])
        tags = self.tags(self.w2a(self.body()))
        self.assertEqual(tags['RESULT'], 'TS')
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')

    def test_a_booking_with_no_price_is_refused_not_paid_for_free(self):
        self.sr.total_price = D('0')
        self.sr.save(update_fields=['total_price'])
        tags = self.tags(self.w2a(self.body(amount=1000)))
        self.assertEqual(tags['ERRORCODE'], yas.E_SERVICE)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_rubbish_instead_of_xml_is_error100(self):
        for body in ('not xml at all', '', '{"json": true}', '<COMMA'):
            r = self.w2a(body)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(self.tags(r)['ERRORCODE'], yas.E_GENERAL,
                             'on %r' % body)

    def test_an_enormous_body_is_refused_without_being_parsed(self):
        r = self.w2a('<COMMAND>' + 'A' * (70 * 1024) + '</COMMAND>')
        self.assertEqual(self.tags(r)['ERRORCODE'], yas.E_GENERAL)
        self.assertIn('too large', self.tags(r)['CONTENT'])

    def test_an_entity_is_never_expanded(self):
        # No XML parser runs, so none of the attacks that come free
        # with XML are available. /etc/passwd stays where it is.
        attack = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE COMMAND [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
            '<COMMAND><TYPE>SYNC_BILLPAY_REQUEST</TYPE>'
            '<CUSTOMERREFERENCEID>&x;</CUSTOMERREFERENCEID>'
            '<AMOUNT>1</AMOUNT></COMMAND>')
        r = self.w2a(attack)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'root:', r.content)
        self.assertEqual(self.tags(r)['ERRORCODE'], yas.E_REF)

    def test_markup_in_a_value_never_reaches_the_reply(self):
        r = self.w2a(self.body(reference='<TYPE>HACKED</TYPE>'))
        # A value holding a tag does not match at all, so the reference
        # arrives empty rather than arriving with markup in it.
        self.assertEqual(r.content.count(b'<TYPE>'), 1)
        self.assertNotIn(b'HACKED', r.content)
        self.assertEqual(self.tags(r)['ERRORCODE'], yas.E_REF)

    def test_what_does_get_through_is_escaped(self):
        body = xml((("TYPE", "SYNC_BILLPAY_REQUEST"), ("TXNID", "BP&1"),
                    ("MSISDN", "0714405395"),
                    ("CUSTOMERREFERENCEID", self.ref),
                    ("AMOUNT", str(int(self.sr.total_price)))))
        r = self.w2a(body)
        self.assertIn(b'BP&amp;1', r.content)
        self.assertEqual(self.tags(r)['TXNID'], 'BP&1')

    def test_an_absurd_amount_does_not_pay_the_booking(self):
        # Decimal parses "1e999999" quite happily, and a number that
        # large sails past the does-it-cover-the-booking check.
        for amount in ('1e999999', '9' * 40, '1E400'):
            sr, _ = self.book()
            sr.payment_status = 'pending'
            sr.save(update_fields=['payment_status'])
            ref = sr.ensure_reference()
            r = self.w2a(self.body(reference=ref, amount=amount))
            self.assertEqual(self.tags(r)['RESULT'], 'TF', 'on %r' % amount)
            sr.refresh_from_db()
            self.assertEqual(sr.payment_status, 'pending', 'on %r' % amount)

    def test_their_tag_case_does_not_lose_a_payment(self):
        body = xml((("Type", "SYNC_BILLPAY_REQUEST"), ("TxnId", "BP1"),
                    ("CustomerReferenceId", self.ref),
                    ("Amount", str(int(self.sr.total_price)))))
        r = self.w2a(body)
        self.assertEqual(self.tags(r)['RESULT'], 'TS')
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')

    def test_referenceid_is_read_when_customerreferenceid_is_absent(self):
        body = xml((("TYPE", "SYNC_BILLPAY_REQUEST"), ("TXNID", "BP2"),
                    ("REFERENCEID", self.ref),
                    ("AMOUNT", str(int(self.sr.total_price)))))
        self.assertEqual(self.tags(self.w2a(body))['RESULT'], 'TS')

    def test_paying_the_same_booking_twice_credits_it_once(self):
        self.w2a(self.body())
        with mock.patch('clients.assignment_mode.apply_assignment_mode') as m:
            second = self.w2a(self.body())
            third = self.w2a(self.body(txnid='BP-SECOND'))
        # The same TXNID again is a retry (TS); a new one is refused (TF).
        self.assertEqual(self.tags(second)['RESULT'], 'TS')
        self.assertEqual(self.tags(third)['RESULT'], 'TF')
        m.assert_not_called()


# ---------------------------------------------------------------------------
# The helpers the outbound half uses
# ---------------------------------------------------------------------------

class ClientHelperTests(FlowBase):
    def test_a_number_is_accepted_however_it_is_written(self):
        for written in ('0714123456', '+255 714 123 456', '255714123456',
                        '714123456', '0714-123-456', ' 0714123456 '):
            self.assertEqual(yas_client.msisdn(written), '255714123456',
                             'on %r' % written)

    def test_what_is_not_a_tanzanian_mobile_comes_back_empty(self):
        for written in ('', None, '0812345678', '12345', '07141234567',
                        'abc', '+44 7700 900000'):
            self.assertEqual(yas_client.msisdn(written), '',
                             'on %r' % written)

    def test_amounts_are_whole_shillings_rounded_down(self):
        self.assertEqual(yas_client.whole_shillings(D('750.90')), 750)
        self.assertEqual(yas_client.whole_shillings('30000'), 30000)
        self.assertEqual(yas_client.whole_shillings(None), 0)

    def test_nothing_is_live_until_it_is_switched_on(self):
        self.assertFalse(yas_client.client_payments_live())
        self.assertFalse(yas_client.worker_payouts_live())

    @override_settings(YAS_CLIENT_PAYMENTS_ENABLED=True,
                       YAS_TOKEN_URL='', YAS_PAY_URL='')
    def test_switched_on_but_unconfigured_is_still_not_live(self):
        self.assertFalse(yas_client.client_payments_live())

    @override_settings(**PAYMENTS_ON)
    def test_switched_on_and_configured_is_live(self):
        self.assertTrue(yas_client.client_payments_live())

    @override_settings(YAS_CLIENT_PAYMENTS_ENABLED=True)
    def test_nothing_is_sent_while_it_is_off(self):
        with override_settings(YAS_CLIENT_PAYMENTS_ENABLED=False):
            with mock.patch.object(yas_client, 'http_requests') as net:
                sent, _ = yas_client.request_payment('0714123456', 1000, 'WC1')
        self.assertFalse(sent)
        net.post.assert_not_called()

    @override_settings(**PAYMENTS_ON)
    def test_a_bad_number_is_not_sent_anywhere(self):
        with mock.patch.object(yas_client, 'http_requests') as net:
            sent, message = yas_client.request_payment('0812345678', 1000,
                                                       'WC1')
        self.assertFalse(sent)
        self.assertIn('Tanzanian', message)
        net.post.assert_not_called()


@override_settings(**PAYMENTS_ON)
class PushRequestTests(FlowBase):
    def setUp(self):
        super().setUp()
        yas_client.forget_token()

    def tearDown(self):
        yas_client.forget_token()
        super().tearDown()

    def reply(self, payload, code=200):
        resp = mock.Mock(status_code=code, content=b'{}')
        resp.json.return_value = payload
        return resp

    def test_a_prompt_is_requested_with_the_fields_they_ask_for(self):
        token = self.reply({'access_token': 'tok', 'expires_in': 3599})
        accepted = self.reply({'ResponseStatus': True,
                               'ResponseCode': 'BILLER-30-0000-S'})
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[token, accepted]) as post:
            sent, message = yas_client.request_payment(
                '0714123456', D('30000.90'), 'WCA1B2C3D4')
        self.assertTrue(sent)
        self.assertIn('Check your phone', message)
        body = post.call_args_list[1].kwargs['json']
        self.assertEqual(body['CustomerMSISDN'], '255714123456')
        # Starts with ours, then a per-attempt marker - see RetryTests.
        self.assertTrue(body['ReferenceID'].startswith('WCA1B2C3D4'),
                        body['ReferenceID'])
        # Whole shillings: a decimal would be refused or quietly rounded.
        self.assertEqual(body['Amount'], 30000)
        self.assertIsInstance(body['Amount'], int)

    @override_settings(YAS_BILLER_CODE='WCX')
    def test_the_biller_code_goes_in_front_of_our_reference(self):
        token = self.reply({'access_token': 'tok'})
        accepted = self.reply({'ResponseStatus': True})
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[token, accepted]) as post:
            yas_client.request_payment('0714123456', 1000, 'WCA1B2C3D4')
        sent = post.call_args_list[1].kwargs['json']['ReferenceID']
        self.assertTrue(sent.startswith('WCXWCA1B2C3D4'), sent)

    def test_a_refused_token_sends_no_payment(self):
        refused = self.reply({'error': 'invalid_grant',
                              'error_description': 'wrong password'})
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[refused]) as post:
            sent, _ = yas_client.request_payment('0714123456', 1000, 'WC1')
        self.assertFalse(sent)
        self.assertEqual(post.call_count, 1)

    def test_a_token_is_reused_rather_than_fetched_every_time(self):
        token = self.reply({'access_token': 'tok', 'expires_in': 3599})
        ok = self.reply({'ResponseStatus': True})
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[token, ok, ok]) as post:
            yas_client.request_payment('0714123456', 1000, 'WC1')
            yas_client.request_payment('0714123456', 1000, 'WC2')
        self.assertEqual(post.call_count, 3)

    def test_an_expired_token_is_refreshed_once(self):
        token = self.reply({'access_token': 'tok', 'expires_in': 3599})
        expired = self.reply({'ResponseStatus': False}, code=401)
        fresh = self.reply({'access_token': 'tok2', 'expires_in': 3599})
        ok = self.reply({'ResponseStatus': True})
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[token, expired, fresh, ok]):
            sent, _ = yas_client.request_payment('0714123456', 1000, 'WC1')
        self.assertTrue(sent)

    def test_a_refusal_is_not_reported_as_a_prompt_on_its_way(self):
        # Claiming a prompt was sent when it was not sends the client to
        # stare at a phone that will never buzz.
        token = self.reply({'access_token': 'tok'})
        refused = self.reply({'ResponseStatus': False,
                              'ResponseDescription': 'Biller not found'})
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[token, refused]):
            sent, message = yas_client.request_payment('0714123456', 1000,
                                                       'WC1')
        self.assertFalse(sent)
        self.assertEqual(message, '')

    def test_a_dead_gateway_is_not_reported_as_a_prompt_on_its_way(self):
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=OSError('connection refused')):
            sent, _ = yas_client.request_payment('0714123456', 1000, 'WC1')
        self.assertFalse(sent)

    def test_html_instead_of_json_does_not_crash(self):
        # Their gateway answers 500 with an HTML error page on routes
        # that belong to other billers.
        token = self.reply({'access_token': 'tok'})
        page = mock.Mock(status_code=500, content=b'<html>Service Not Found')
        page.json.side_effect = ValueError('not json')
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[token, page]):
            sent, _ = yas_client.request_payment('0714123456', 1000, 'WC1')
        self.assertFalse(sent)

    def test_the_password_is_never_written_to_the_log(self):
        token = self.reply({'access_token': 'tok'})
        ok = self.reply({'ResponseStatus': True})
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[token, ok]):
            with self.assertLogs('worker_connect.yas', level='INFO') as caught:
                yas_client.request_payment('0714123456', 1000, 'WC1')
        self.assertNotIn('secret-password', '\n'.join(caught.output))


# ---------------------------------------------------------------------------
# Payouts
# ---------------------------------------------------------------------------

class PayoutReferenceTests(FlowBase):
    def test_a_payout_reference_is_exactly_twenty_characters(self):
        # The specification states the length as 20 and a gateway
        # truncates a long field rather than complaining - and a
        # truncated reference is a payout we cannot match to a worker.
        ref = yas.new_payout_reference()
        self.assertEqual(len(ref), 20)
        self.assertRegex(ref, r'^CI\d{18}$')

    def test_payout_references_do_not_repeat(self):
        self.assertEqual(len({yas.new_payout_reference()
                              for _ in range(200)}), 200)


class PayoutCreationTests(FlowBase):
    def test_the_workers_mixx_number_is_copied_onto_the_row(self):
        MobileMoneyAccount.objects.create(
            user=self.worker_user, provider='tigo_pesa',
            phone_number='0714123456', account_name='Wor Ker',
            is_default=True, is_verified=True)
        payout = make_payout(self, D('25000'),
                                          created_by=self.admin)
        # Copied, not read at send time: a profile edited between
        # approval and sending must not redirect the money.
        self.assertEqual(payout.phone_number, '0714123456')
        self.assertEqual(payout.state, 'pending')
        self.assertEqual(payout.created_by_id, self.admin.id)

    def test_without_a_verified_wallet_there_is_no_default_number(self):
        # The account phone is edited freely, so it is not a destination.
        with self.assertRaises(yas_client.PayoutRefused):
            yas_client.create_payout(
                self.wp, D('25000'), created_by=self.admin,
                service_request=completed_job(self))

    def test_making_a_payout_sends_nothing(self):
        with mock.patch.object(yas_client, 'http_requests') as net:
            make_payout(self, D('25000'))
        net.post.assert_not_called()


@override_settings(**PAYOUTS_ON)
class PayoutSendTests(FlowBase):
    def setUp(self):
        super().setUp()
        MobileMoneyAccount.objects.create(
            user=self.worker_user, provider='tigo_pesa',
            phone_number='0714123456', account_name='Wor Ker',
            is_default=True, is_verified=True)
        self.payout = make_payout(self, D('25000.90'),
                                               created_by=self.admin)

    def answer(self, text, code=200):
        return mock.Mock(status_code=code, text=text)

    def send(self, text=None, error=None):
        kwargs = ({'side_effect': error} if error
                  else {'return_value': self.answer(text)})
        with mock.patch.object(yas_client.http_requests, 'post',
                               **kwargs) as post:
            state, message = yas_client.send_payout(self.payout)
        self.payout.refresh_from_db()
        return state, message, post

    def test_status_200_is_paid(self):
        state, message, _ = self.send(resmfici('200'))
        self.assertEqual(state, 'paid')
        self.assertEqual(self.payout.state, 'paid')
        self.assertEqual(self.payout.yas_txnid, '42326232')
        self.assertIsNotNone(self.payout.settled_at)
        self.assertIn('25000', message)

    def test_status_zero_is_also_paid(self):
        self.assertEqual(self.send(resmfici('0'))[0], 'paid')

    def test_status_100_is_held_not_failed(self):
        # The specification asks for this in so many words: "Partner
        # should put transaction amount in HOLD state to avoid risk of
        # rollback while amount was disbursed." Marking it failed
        # invites a second payout for money that may already have gone.
        state, message, _ = self.send(resmfici('100', message='General error'))
        self.assertEqual(state, 'held')
        self.assertEqual(self.payout.state, 'held')
        self.assertTrue(self.payout.needs_a_person)
        self.assertIsNone(self.payout.settled_at)
        self.assertIn('unknown', message)
        self.assertIn(self.payout.reference, message)

    def test_a_timeout_is_held(self):
        # "This is the same case for any kind of timeout as well."
        state, message, _ = self.send(error=OSError('timed out'))
        self.assertEqual(state, 'held')
        self.assertIn('did not answer', message)

    def test_an_unreadable_answer_is_held(self):
        self.assertEqual(self.send('<html>Gateway Error</html>')[0], 'held')

    def test_a_published_refusal_is_failed_and_explained_in_words(self):
        state, message, _ = self.send(resmfici('60019'))
        self.assertEqual(state, 'failed')
        self.assertIn('minimum balance', message)
        self.assertEqual(self.payout.yas_status, '60019')

    def test_an_unpublished_refusal_quotes_their_own_text(self):
        state, message, _ = self.send(
            resmfici('99999', message='Something they invented'))
        self.assertEqual(state, 'failed')
        self.assertIn('Something they invented', message)

    def test_the_envelope_is_what_the_specification_asks_for(self):
        _state, _m, post = self.send(resmfici('200'))
        body = post.call_args.kwargs['data'].decode()
        tags = yas_client._read_response(body)
        self.assertEqual(tags['TYPE'], 'REQMFICI')
        self.assertEqual(tags['REFERENCEID'], self.payout.reference)
        self.assertEqual(tags['MSISDN'], '255691511330')
        self.assertEqual(tags['PIN'], '1456')
        self.assertEqual(tags['MSISDN1'], '255714123456')
        # Whole shillings, rounded down: never send a worker a shilling
        # we did not owe.
        self.assertEqual(tags['AMOUNT'], '25000')
        self.assertEqual(tags['BRAND_ID'], '1232')
        self.assertEqual(tags['SENDERNAME'], 'Worker Search')
        self.assertEqual(tags['LANGUAGE1'], 'en')
        self.assertIn('xml', post.call_args.kwargs['headers']['Content-Type'])

    def test_the_pin_is_never_written_to_the_log(self):
        with mock.patch.object(yas_client.http_requests, 'post',
                               return_value=self.answer(resmfici('200'))):
            with self.assertLogs('worker_connect.yas', level='INFO') as caught:
                yas_client.send_payout(self.payout)
        self.assertNotIn('1456', '\n'.join(caught.output))

    def test_a_paid_payout_cannot_be_sent_again(self):
        self.send(resmfici('200'))
        with mock.patch.object(yas_client.http_requests, 'post') as post:
            state, message = yas_client.send_payout(self.payout)
        post.assert_not_called()
        self.assertEqual(state, 'paid')
        self.assertIn('already been paid', message)

    def test_a_held_payout_is_not_retried_automatically(self):
        self.send(resmfici('100'))
        with mock.patch.object(yas_client.http_requests, 'post') as post:
            state, message = yas_client.send_payout(self.payout)
        post.assert_not_called()
        self.assertEqual(state, 'held')
        self.assertIn('statement', message)

    def test_two_admins_pressing_at_once_send_once(self):
        # The claim is a conditional update, so whichever one changes no
        # rows stops before the gateway is called.
        WorkerPayout.objects.filter(pk=self.payout.pk).update(state='sending')
        with mock.patch.object(yas_client.http_requests, 'post') as post:
            state, _ = yas_client.send_payout(self.payout)
        post.assert_not_called()
        self.assertEqual(state, 'sending')

    @override_settings(YAS_WORKER_PAYOUTS_ENABLED=False)
    def test_nothing_is_sent_while_payouts_are_off(self):
        with mock.patch.object(yas_client, 'http_requests') as net:
            state, message = yas_client.send_payout(self.payout)
        net.post.assert_not_called()
        self.assertEqual(state, 'pending')
        self.assertIn('not switched on', message)

    def test_a_bad_number_is_not_sent_anywhere(self):
        self.payout.phone_number = '0812345678'
        self.payout.save(update_fields=['phone_number'])
        with mock.patch.object(yas_client, 'http_requests') as net:
            state, message = yas_client.send_payout(self.payout)
        net.post.assert_not_called()
        self.assertEqual(state, 'pending')
        self.assertIn('Tanzanian', message)


# ---------------------------------------------------------------------------
# The endpoints a person reaches
# ---------------------------------------------------------------------------

class ClientEndpointTests(YasBase):
    def pay_url(self, sr=None):
        return '/api/v1/payments/yas/pay/%s/' % (sr or self.sr).id

    def test_paying_is_unavailable_while_it_is_off(self):
        r = post_json(self.client_c, self.pay_url(), {})
        self.assertEqual(r.status_code, 503)
        self.assertIn('not available yet', r.json()['error'])

    def test_a_stranger_cannot_make_somebody_elses_phone_ring(self):
        other = self.client.__class__()
        other.force_login(self.other_client)
        r = post_json(other, self.pay_url(), {})
        self.assertEqual(r.status_code, 404)

    def test_signing_in_is_required(self):
        r = post_json(self.client.__class__(), self.pay_url(), {})
        self.assertIn(r.status_code, (401, 403))

    @override_settings(**PAYMENTS_ON)
    def test_an_already_paid_booking_is_not_charged_again(self):
        self.sr.mark_paid_by_gateway('earlier')
        r = post_json(self.client_c, self.pay_url(), {})
        self.assertEqual(r.status_code, 400)
        self.assertIn('already paid', r.json()['error'])

    @override_settings(**PAYMENTS_ON)
    def test_a_prompt_is_requested_and_nothing_is_marked_paid(self):
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(True, 'Check your phone.')) as rp:
            r = post_json(self.client_c, self.pay_url(),
                          {'phone_number': '0714123456'})
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body['status'], 'prompt_sent')
        self.assertEqual(body['reference'], self.ref)
        rp.assert_called_once()
        # The money arrives at the callback. Treating acceptance as
        # payment would confirm bookings nobody paid for.
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    @override_settings(**PAYMENTS_ON)
    def test_a_bad_number_is_refused_before_anything_is_sent(self):
        with mock.patch.object(yas_client, 'request_payment') as rp:
            r = post_json(self.client_c, self.pay_url(),
                          {'phone_number': '0812345678'})
        self.assertEqual(r.status_code, 400)
        rp.assert_not_called()

    @override_settings(**PAYMENTS_ON)
    def test_a_refusal_from_yas_is_a_502_not_a_success(self):
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(False, '')):
            r = post_json(self.client_c, self.pay_url(),
                          {'phone_number': '0714123456'})
        self.assertEqual(r.status_code, 502)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'pending')

    def test_the_instructions_name_the_reference_to_type(self):
        # This way needs no switch: it is only telling them a reference.
        r = self.client_c.get(
            '/api/v1/payments/yas/instructions/%s/' % self.sr.id)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body['reference'], self.ref)
        self.assertFalse(body['paid'])
        self.assertTrue(any(self.ref in step for step in body['steps']))

    def test_the_instructions_mint_a_reference_for_an_older_booking(self):
        sr, _ = self.book()
        ServiceRequest.objects.filter(pk=sr.pk).update(reference=None)
        r = self.client_c.get(
            '/api/v1/payments/yas/instructions/%s/' % sr.id)
        self.assertEqual(r.status_code, 200)
        self.assertRegex(r.json()['reference'], r'^WC[A-Z0-9]{8}$')

    def test_a_stranger_cannot_read_the_instructions(self):
        other = self.client.__class__()
        other.force_login(self.other_client)
        r = other.get('/api/v1/payments/yas/instructions/%s/' % self.sr.id)
        self.assertEqual(r.status_code, 404)


class AdminEndpointTests(FlowBase):
    def setUp(self):
        super().setUp()
        MobileMoneyAccount.objects.create(
            user=self.worker_user, provider='tigo_pesa',
            phone_number='0714123456', account_name='Wor Ker',
            is_default=True, is_verified=True)

    def test_a_client_cannot_see_the_payouts(self):
        self.assertIn(self.client_c.get('/api/v1/payments/yas/payouts/')
                      .status_code, (401, 403))

    def test_a_worker_cannot_pay_themselves(self):
        payout = make_payout(self, D('25000'))
        r = post_json(self.worker_c,
                      '/api/v1/payments/yas/payouts/%s/send/' % payout.id, {})
        self.assertIn(r.status_code, (401, 403))

    def test_an_admin_creates_a_payout_and_nothing_is_sent(self):
        job = completed_job(self)
        with mock.patch.object(yas_client, 'http_requests') as net:
            r = post_json(self.admin_c, '/api/v1/payments/yas/payouts/',
                          {'worker_id': self.wp.id, 'amount': '25000',
                           'service_request_id': job.id})
        self.assertEqual(r.status_code, 201, r.content)
        net.post.assert_not_called()
        self.assertEqual(r.json()['state'], 'pending')
        self.assertEqual(r.json()['phone_number'], '0714123456')

    def test_a_payout_needs_a_worker_and_an_amount(self):
        for body in ({}, {'worker_id': self.wp.id},
                     {'worker_id': self.wp.id, 'amount': '0'},
                     {'worker_id': self.wp.id, 'amount': '-5'},
                     {'worker_id': self.wp.id, 'amount': 'abc'}):
            r = post_json(self.admin_c, '/api/v1/payments/yas/payouts/', body)
            self.assertEqual(r.status_code, 400, 'on %r' % body)

    def test_an_unknown_worker_is_404(self):
        r = post_json(self.admin_c, '/api/v1/payments/yas/payouts/',
                      {'worker_id': 999999, 'amount': '1000'})
        self.assertEqual(r.status_code, 404)

    def test_a_worker_with_no_usable_number_is_flagged_at_once(self):
        MobileMoneyAccount.objects.all().delete()
        self.worker2_user.phone_number = ''
        self.worker2_user.save(update_fields=['phone_number'])
        job = completed_job(self, wp=self.wp2)
        r = post_json(self.admin_c, '/api/v1/payments/yas/payouts/',
                      {'worker_id': self.wp2.id, 'amount': '1000',
                       'service_request_id': job.id})
        self.assertEqual(r.status_code, 400)
        self.assertIn('no verified Mixx by Yas wallet', r.json()['error'])

    def test_sending_is_unavailable_while_payouts_are_off(self):
        payout = make_payout(self, D('25000'))
        with mock.patch.object(yas_client, 'http_requests') as net:
            r = post_json(self.admin_c,
                          '/api/v1/payments/yas/payouts/%s/send/' % payout.id,
                          {})
        self.assertEqual(r.status_code, 503)
        net.post.assert_not_called()

    @override_settings(**PAYOUTS_ON)
    def test_a_held_payout_answers_202_not_200(self):
        payout = make_payout(self, D('25000'))
        with mock.patch.object(yas_client.http_requests, 'post',
                               return_value=mock.Mock(
                                   status_code=200, text=resmfici('100'))):
            r = post_json(self.admin_c,
                          '/api/v1/payments/yas/payouts/%s/send/' % payout.id,
                          {})
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json()['state'], 'held')
        self.assertTrue(r.json()['needs_a_person'])

    @override_settings(**PAYOUTS_ON)
    def test_a_paid_payout_answers_200(self):
        payout = make_payout(self, D('25000'))
        with mock.patch.object(yas_client.http_requests, 'post',
                               return_value=mock.Mock(
                                   status_code=200, text=resmfici('200'))):
            r = post_json(self.admin_c,
                          '/api/v1/payments/yas/payouts/%s/send/' % payout.id,
                          {})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['state'], 'paid')

    def test_only_a_held_payout_is_resolved_by_hand(self):
        payout = make_payout(self, D('25000'))
        r = post_json(self.admin_c,
                      '/api/v1/payments/yas/payouts/%s/resolve/' % payout.id,
                      {'outcome': 'paid'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('held', r.json()['error'])

    def test_a_held_payout_is_resolved_by_a_person_who_looked(self):
        payout = make_payout(self, D('25000'))
        WorkerPayout.objects.filter(pk=payout.pk).update(state='held')
        r = post_json(self.admin_c,
                      '/api/v1/payments/yas/payouts/%s/resolve/' % payout.id,
                      {'outcome': 'paid', 'note': 'on the 12 Nov statement'})
        self.assertEqual(r.status_code, 200, r.content)
        payout.refresh_from_db()
        self.assertEqual(payout.state, 'paid')
        self.assertIsNotNone(payout.settled_at)
        # Who decided, and on what evidence, is the point of the record.
        self.assertIn('12 Nov statement', payout.yas_message)
        self.assertIn('boss', payout.yas_message)

    def test_resolving_needs_a_real_outcome(self):
        payout = make_payout(self, D('25000'))
        WorkerPayout.objects.filter(pk=payout.pk).update(state='held')
        for outcome in ({}, {'outcome': 'maybe'}, {'outcome': 'held'}):
            r = post_json(
                self.admin_c,
                '/api/v1/payments/yas/payouts/%s/resolve/' % payout.id,
                outcome)
            self.assertEqual(r.status_code, 400, 'on %r' % outcome)

    def test_held_payouts_are_counted_where_an_admin_will_see_them(self):
        for _ in range(3):
            p = make_payout(self, D('1000'))
            WorkerPayout.objects.filter(pk=p.pk).update(state='held')
        r = self.admin_c.get('/api/v1/payments/yas/payouts/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['held'], 3)

    def test_the_payout_list_can_be_narrowed(self):
        p = make_payout(self, D('1000'))
        WorkerPayout.objects.filter(pk=p.pk).update(state='held')
        make_payout(self, D('2000'))
        r = self.admin_c.get('/api/v1/payments/yas/payouts/?state=held')
        self.assertEqual(r.json()['count'], 1)


class StatusEndpointTests(FlowBase):
    def test_a_client_cannot_read_it(self):
        self.assertIn(self.client_c.get(STATUS).status_code, (401, 403))

    def test_it_says_everything_is_off_and_what_is_missing(self):
        r = self.admin_c.get(STATUS)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertFalse(body['client_payments']['switched_on'])
        self.assertFalse(body['client_payments']['working'])
        self.assertFalse(body['worker_payouts']['switched_on'])
        self.assertIn('token_url', body['missing'])
        self.assertIn('disbursement_pin', body['missing'])
        self.assertIn('YAS_CLIENT_PAYMENTS_ENABLED', body['how_to_switch_on'])

    @override_settings(**PAYMENTS_ON)
    def test_it_reports_client_payments_working(self):
        body = self.admin_c.get(STATUS).json()
        self.assertTrue(body['client_payments']['working'])
        self.assertTrue(body['settings_present']['biller_password'])

    @override_settings(**dict(PAYMENTS_ON, **PAYOUTS_ON))
    def test_it_never_hands_back_a_credential(self):
        # This sits on an admin screen and in screenshots.
        raw = json.dumps(self.admin_c.get(STATUS).json())
        for secret in ('secret-password', '1456', SECRET,
                       'wc-partner-login'):
            self.assertNotIn(secret, raw)

    def test_it_counts_the_payouts_that_need_a_person(self):
        p = make_payout(self, D('1000'))
        WorkerPayout.objects.filter(pk=p.pk).update(state='held')
        body = self.admin_c.get(STATUS).json()
        self.assertEqual(body['payouts']['held'], 1)


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------

class RefundReferenceTests(FlowBase):
    def test_a_refund_reference_is_twenty_characters(self):
        ref = yas.new_refund_reference()
        self.assertEqual(len(ref), 20)
        self.assertRegex(ref, r'^RF\d{18}$')

    def test_refund_references_do_not_repeat(self):
        self.assertEqual(len({yas.new_refund_reference()
                              for _ in range(200)}), 200)

    def test_a_refund_reference_is_not_a_payout_reference(self):
        # Two different kinds of outgoing money must never collide in
        # the statement, so they do not share a prefix.
        self.assertNotEqual(yas.new_refund_reference()[:2],
                            yas.new_payout_reference()[:2])


class RefundCreationTests(YasBase):
    def test_approving_a_refund_sends_nothing(self):
        with mock.patch.object(yas_client, 'http_requests') as net:
            refund = make_refund(self, self.sr.total_price, '0714123456')
        net.post.assert_not_called()
        self.assertEqual(refund.state, 'pending')
        self.assertEqual(refund.client_id, self.sr.client_id)

    def test_the_clients_number_is_copied_onto_the_row(self):
        # The paying wallet, as recorded at pay time.
        refund = make_refund(self, D('1000'), '0714123456')
        self.assertEqual(refund.phone_number, '255714123456')


@override_settings(**REFUNDS_ON)
class RefundSendTests(YasBase):
    def setUp(self):
        super().setUp()
        yas_client.forget_token()
        yas.settle(self.sr, '26797615656', amount=self.sr.total_price,
                   gateway_reference=self.ref, payer_msisdn='255714123456')
        self.refund = make_refund(self,D('30000.90'), '0714123456', created_by=self.admin,
            reason='paid the wrong amount',
            mfs_transaction_id='26797615656',
            purchase_reference=self.ref)

    def tearDown(self):
        yas_client.forget_token()
        super().tearDown()

    def reply(self, payload, code=200):
        resp = mock.Mock(status_code=code, content=b'{}')
        resp.json.return_value = payload
        return resp

    def send(self, payload=None, error=None, token_fails=False):
        token = (self.reply({'error': 'invalid_grant'}) if token_fails
                 else self.reply({'access_token': 'tok', 'expires_in': 3599}))
        if error:
            effects = [token, error]
        elif token_fails:
            effects = [token]
        else:
            effects = [token, self.reply(payload)]
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=effects) as post:
            state, message = yas_client.send_refund(self.refund)
        self.refund.refresh_from_db()
        return state, message, post

    def test_a_success_is_recorded_as_refunded(self):
        state, message, _ = self.send({
            'ResponseCode': 'REVERSE-20-0000-S',
            'ResponseStatus': True,
            'ResponseDescription': 'Reverse Transaction Success',
            'DMReferenceID': 'ATCTes20170721546548w'})
        self.assertEqual(state, 'paid')
        self.assertEqual(self.refund.state, 'paid')
        self.assertEqual(self.refund.yas_reference, 'ATCTes20170721546548w')
        self.assertIsNotNone(self.refund.settled_at)
        self.assertIn('30000', message)

    def test_a_refusal_is_recorded_as_failed_with_their_words(self):
        state, message, _ = self.send({
            'ResponseCode': 'DebitMandate-10-5000-E',
            'ResponseStatus': False,
            'ResponseDescription': 'Original transaction not found'})
        self.assertEqual(state, 'failed')
        self.assertIn('not found', message)
        self.assertEqual(self.refund.yas_code, 'DebitMandate-10-5000-E')

    def test_no_answer_is_held_not_failed(self):
        # Money may have moved. Saying it certainly did not is the one
        # answer that gets a client paid back twice.
        state, message, _ = self.send(error=OSError('timed out'))
        self.assertEqual(state, 'held')
        self.assertTrue(self.refund.needs_a_person)
        self.assertIn('did not answer', message)
        self.assertIn(self.refund.reference, message)

    def test_an_unclear_answer_is_held(self):
        for payload in ({}, {'ResponseCode': 'x'},
                        {'ResponseStatus': 'maybe'}):
            self.refund.state = 'pending'
            self.refund.save(update_fields=['state'])
            state, _m, _p = self.send(payload)
            self.assertEqual(state, 'held', 'on %r' % payload)

    def test_the_body_is_what_the_specification_asks_for(self):
        _state, _m, post = self.send({'ResponseStatus': True})
        body = post.call_args_list[1].kwargs['json']
        self.assertEqual(body['CustomerMSISDN'], '255714123456')
        self.assertEqual(body['ChannelMSISDN'], '255691511330')
        self.assertEqual(body['ChannelPIN'], '1234')
        # Whole shillings, rounded down.
        self.assertEqual(body['Amount'], '30000')
        self.assertEqual(body['ReferenceID'], self.refund.reference)
        self.assertEqual(body['MFSTransactionID'], '26797615656')
        self.assertEqual(body['PurchaseReferenceID'], self.ref)
        headers = post.call_args_list[1].kwargs['headers']
        self.assertTrue(headers['Authorization'].startswith('bearer '))

    def test_the_pin_and_password_are_never_logged(self):
        with mock.patch.object(
                yas_client.http_requests, 'post',
                side_effect=[self.reply({'access_token': 'tok'}),
                             self.reply({'ResponseStatus': True})]):
            with self.assertLogs('worker_connect.yas', level='INFO') as caught:
                yas_client.send_refund(self.refund)
        written = chr(10).join(caught.output)
        self.assertNotIn('1234', written)
        self.assertNotIn('secret-password', written)

    def test_a_refund_with_nothing_to_match_is_not_sent(self):
        # Their gateway only reverses a payment it can find, and with
        # neither the transaction id nor the reference it cannot.
        self.refund.mfs_transaction_id = ''
        self.refund.purchase_reference = ''
        self.refund.save(update_fields=['mfs_transaction_id',
                                        'purchase_reference'])
        with mock.patch.object(yas_client, 'http_requests') as net:
            state, message = yas_client.send_refund(self.refund)
        net.post.assert_not_called()
        self.assertEqual(state, 'pending')
        self.assertIn('cannot find the payment', message)

    def test_a_refused_token_leaves_it_sendable(self):
        # Nothing went out, so this one may be tried again - unlike a
        # call that went out and was not answered.
        state, message, _ = self.send(token_fails=True)
        self.assertEqual(state, 'pending')
        self.assertIn('nothing was sent', message)

    def test_a_sent_refund_cannot_be_sent_again(self):
        self.send({'ResponseStatus': True})
        with mock.patch.object(yas_client, 'http_requests') as net:
            state, message = yas_client.send_refund(self.refund)
        net.post.assert_not_called()
        self.assertEqual(state, 'paid')
        self.assertIn('already been sent', message)

    def test_a_held_refund_is_not_retried_automatically(self):
        self.send(error=OSError('timed out'))
        with mock.patch.object(yas_client, 'http_requests') as net:
            state, message = yas_client.send_refund(self.refund)
        net.post.assert_not_called()
        self.assertEqual(state, 'held')
        self.assertIn('statement', message)

    def test_a_bad_number_is_not_sent_anywhere(self):
        self.refund.phone_number = '0812345678'
        self.refund.save(update_fields=['phone_number'])
        with mock.patch.object(yas_client, 'http_requests') as net:
            state, message = yas_client.send_refund(self.refund)
        net.post.assert_not_called()
        self.assertEqual(state, 'pending')
        self.assertIn('Tanzanian', message)

    @override_settings(YAS_REFUNDS_ENABLED=False)
    def test_nothing_is_sent_while_refunds_are_off(self):
        with mock.patch.object(yas_client, 'http_requests') as net:
            state, message = yas_client.send_refund(self.refund)
        net.post.assert_not_called()
        self.assertEqual(state, 'pending')
        self.assertIn('not switched on', message)


class RefundEndpointTests(YasBase):
    def test_a_client_cannot_refund_themselves(self):
        r = post_json(self.client_c, '/api/v1/payments/yas/refunds/',
                      {'service_request_id': self.sr.id})
        self.assertIn(r.status_code, (401, 403))

    def test_an_admin_approves_a_refund_and_nothing_is_sent(self):
        yas.settle(self.sr, '26797615656', amount=self.sr.total_price,
                   gateway_reference=self.ref)
        with mock.patch.object(yas_client, 'http_requests') as net:
            r = post_json(self.admin_c, '/api/v1/payments/yas/refunds/',
                          {'service_request_id': self.sr.id,
                           'reason': 'paid the wrong amount'})
        self.assertEqual(r.status_code, 201, r.content)
        net.post.assert_not_called()
        body = r.json()
        self.assertEqual(body['state'], 'pending')
        # Filled in from the booking, which is the case this exists for.
        self.assertEqual(body['amount'], str(self.sr.total_price))
        self.assertEqual(body['mfs_transaction_id'], '26797615656')
        self.assertEqual(body['purchase_reference'], self.ref)

    def test_a_refund_needs_a_booking(self):
        for body in ({}, {'service_request_id': 999999}):
            r = post_json(self.admin_c, '/api/v1/payments/yas/refunds/', body)
            self.assertIn(r.status_code, (400, 404), 'on %r' % body)

    def test_a_refund_amount_must_be_more_than_zero(self):
        for amount in ('0', '-100', 'abc'):
            r = post_json(self.admin_c, '/api/v1/payments/yas/refunds/',
                          {'service_request_id': self.sr.id,
                           'amount': amount})
            self.assertEqual(r.status_code, 400, 'on %r' % amount)

    def test_a_booking_never_paid_by_yas_cannot_be_refunded(self):
        # Refused at approval now, rather than warned about: there is no
        # original payment for YAS to reverse.
        r = post_json(self.admin_c, '/api/v1/payments/yas/refunds/',
                      {'service_request_id': self.sr.id, 'amount': '1000'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('no Mixx by Yas payment', r.json()['error'])

    def test_sending_is_unavailable_while_refunds_are_off(self):
        refund = make_refund(self, D('1000'), '0714123456')
        with mock.patch.object(yas_client, 'http_requests') as net:
            r = post_json(
                self.admin_c,
                '/api/v1/payments/yas/refunds/%s/send/' % refund.id, {})
        self.assertEqual(r.status_code, 503)
        net.post.assert_not_called()

    @override_settings(**REFUNDS_ON)
    def test_a_held_refund_answers_202(self):
        refund = make_refund(self, D('1000'), '0714123456',
            mfs_transaction_id='26797615656')
        yas_client.forget_token()
        token = mock.Mock(status_code=200, content=b'{}')
        token.json.return_value = {'access_token': 'tok'}
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=[token, OSError('timed out')]):
            r = post_json(
                self.admin_c,
                '/api/v1/payments/yas/refunds/%s/send/' % refund.id, {})
        yas_client.forget_token()
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json()['state'], 'held')
        self.assertTrue(r.json()['needs_a_person'])

    def test_only_a_held_refund_is_resolved_by_hand(self):
        refund = make_refund(self, D('1000'), '0714123456')
        r = post_json(
            self.admin_c,
            '/api/v1/payments/yas/refunds/%s/resolve/' % refund.id,
            {'outcome': 'paid'})
        self.assertEqual(r.status_code, 400)

    def test_a_held_refund_is_resolved_by_a_person_who_looked(self):
        refund = make_refund(self, D('1000'), '0714123456')
        ClientRefund.objects.filter(pk=refund.pk).update(state='held')
        r = post_json(
            self.admin_c,
            '/api/v1/payments/yas/refunds/%s/resolve/' % refund.id,
            {'outcome': 'failed', 'note': 'never left, per the statement'})
        self.assertEqual(r.status_code, 200, r.content)
        refund.refresh_from_db()
        self.assertEqual(refund.state, 'failed')
        self.assertIn('never left', refund.yas_message)
        self.assertIn('boss', refund.yas_message)

    def test_held_refunds_are_counted_where_an_admin_will_see_them(self):
        for _ in range(2):
            refund = make_refund(self, D('1000'),
                                              '0714123456')
            ClientRefund.objects.filter(pk=refund.pk).update(state='held')
        r = self.admin_c.get('/api/v1/payments/yas/refunds/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['held'], 2)

    def test_the_status_screen_counts_refunds_waiting(self):
        refund = make_refund(self, D('1000'), '0714123456')
        ClientRefund.objects.filter(pk=refund.pk).update(state='held')
        body = self.admin_c.get(STATUS).json()
        self.assertEqual(body['refunds_waiting']['held'], 1)
        self.assertFalse(body['refunds']['switched_on'])
        self.assertIn('refund_url', body['missing'])


class ReferenceExposureTests(YasBase):
    """Where the reference may be seen, and where it may not.

    It is quasi-secret. Not a password - knowing it lets somebody pay
    for a booking, not read it - but publishing it undoes the reason the
    field exists instead of using the row id.
    """

    def test_the_client_can_see_their_own_reference(self):
        r = self.client_c.get(
            '/api/v1/client/service-requests/%s/' % self.sr.id)
        self.assertEqual(r.status_code, 200, r.content)
        # The view nests the booking under 'service_request'.
        self.assertEqual(r.json()['service_request']['reference'], self.ref)

    def test_a_client_cannot_set_their_own_reference(self):
        # Read-only on purpose: a client who could set it could attach
        # somebody else's reference to their own job.
        before = self.sr.reference
        r = patch_json(self.client_c,
                       '/api/v1/client/service-requests/%s/update/'
                       % self.sr.id,
                       {'reference': 'WCSTOLEN01'})
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.reference, before, r.content)

    def test_the_public_job_search_does_not_publish_it(self):
        # This endpoint is AllowAny, and it has leaked clients' names
        # and phone numbers once before.
        r = self.client.get('/api/v1/search/jobs/')
        if r.status_code == 200:
            self.assertNotIn(self.ref, r.content.decode('utf-8', 'replace'))

    def test_a_stranger_cannot_read_the_booking_at_all(self):
        other = self.client.__class__()
        other.force_login(self.other_client)
        r = other.get('/api/v1/client/service-requests/%s/' % self.sr.id)
        self.assertIn(r.status_code, (403, 404))
        if r.status_code == 200:
            self.assertNotIn(self.ref, r.content.decode('utf-8', 'replace'))


@override_settings(**PAYMENTS_ON)
class RetryTests(YasBase):
    """A client whose PIN fails has to be able to try again.

    The Debit Mandate specification calls ReferenceID "a unique
    reference ID, which can be used to track the request" (p.8) - per
    request, not per booking - and their own sample is the biller code
    followed by a timestamp.

    Sending the booking reference unchanged every time is why a retry
    on the other platform comes back DuplicateRefID and looks like our
    fault.
    """

    def setUp(self):
        super().setUp()
        yas_client.forget_token()

    def tearDown(self):
        yas_client.forget_token()
        super().tearDown()

    def reply(self, payload, code=200):
        resp = mock.Mock(status_code=code, content=b'{}')
        resp.json.return_value = payload
        return resp

    def references_sent(self, attempts=2):
        token = self.reply({'access_token': 'tok', 'expires_in': 3599})
        ok = self.reply({'ResponseStatus': True})
        effects = [token] + [ok] * attempts
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=effects) as post:
            for _ in range(attempts):
                yas_client.request_payment('0714123456',
                                           self.sr.total_price, self.ref)
        return [call.kwargs['json']['ReferenceID']
                for call in post.call_args_list
                if 'json' in call.kwargs]

    def test_two_attempts_send_two_different_references(self):
        sent = self.references_sent(2)
        self.assertEqual(len(sent), 2)
        self.assertNotEqual(sent[0], sent[1], sent)

    def test_many_attempts_in_a_row_never_repeat(self):
        # Eight was enough to catch a marker with only two random
        # digits behind a one-second clock. Fifty, as fast as the
        # machine will send them, is the real bar.
        sent = self.references_sent(50)
        self.assertEqual(len(set(sent)), 50,
                         "repeats: %s" % sorted(
                             r for r in set(sent) if sent.count(r) > 1))

    def test_the_booking_reference_is_still_inside_what_is_sent(self):
        sent = self.references_sent(1)
        self.assertIn(self.ref, sent[0])

    def test_the_callback_still_resolves_what_we_sent(self):
        # The whole fix rests on this: a longer reference goes out, and
        # the one that comes home still finds the booking.
        for sent in self.references_sent(4):
            self.assertEqual(yas.request_ref_from(sent), self.ref,
                             'on %r' % sent)

    @override_settings(YAS_BILLER_CODE='JMB')
    def test_it_resolves_with_a_biller_code_in_front_as_well(self):
        for sent in self.references_sent(3):
            self.assertTrue(sent.startswith('JMB'), sent)
            self.assertEqual(yas.request_ref_from(sent), self.ref,
                             'on %r' % sent)

    def test_a_real_callback_pays_the_booking_after_a_retry(self):
        sent = self.references_sent(2)[-1]
        r = self.push({'ReferenceID': sent, 'Status': 'true',
                       'Amount': int(self.sr.total_price),
                       'MFSTransactionID': '26797615656'})
        self.assertEqual(r.status_code, 200)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')

    def test_the_marker_is_digits_only(self):
        # Appended rather than inserted, and digits only, so the
        # booking reference stays the first thing found inside it.
        marker = yas_client.new_attempt_marker()
        self.assertTrue(marker.isdigit(), marker)
        # Seconds (14) plus eight random digits.
        self.assertEqual(len(marker), 22)

    def test_the_whole_reference_stays_inside_the_only_length_they_state(self):
        # YAS give no maximum for this field. The only reference length
        # they put in writing is CUSTOMERREFERENCEID at 50 characters.
        with override_settings(YAS_BILLER_CODE='EASYFIX'):
            sent = yas_client.reference_for(
                self.ref, yas_client.new_attempt_marker())
        self.assertLessEqual(len(sent), 50, sent)

    def test_what_a_client_types_is_still_short(self):
        # Only the outgoing push reference grows. The one a client
        # keys into the Mixx menu by hand must stay typeable.
        r = self.client_c.get(
            '/api/v1/payments/yas/instructions/%s/' % self.sr.id)
        self.assertEqual(r.json()['reference'], self.ref)
        self.assertEqual(len(r.json()['reference']), 10)


@override_settings(**IDENTIFIED)
class LiveBookingShapeTests(FlowBase):
    """A booking exactly as the live site makes them.

    YasBase clears the demo PaymentTransaction so the other tests start
    from a clean booking. These deliberately do not: every booking made
    through the app holds a demo reference in PaymentTransaction's
    consumed_by, which is a OneToOne, and that is the shape a real YAS
    payment will actually meet in production.
    """

    def setUp(self):
        super().setUp()
        self.sr, self.demo_ref = self.book()
        self.sr.payment_status = 'pending'
        self.sr.payment_verified = False
        self.sr.paid_at = None
        self.sr.save()
        self.ref = self.sr.ensure_reference()

    def test_the_demo_reference_really_is_in_the_way(self):
        # If this ever stops being true the tests below are testing
        # nothing, so it is asserted rather than assumed.
        self.assertTrue(PaymentTransaction.objects.filter(
            consumed_by=self.sr, is_demo=True).exists())

    def test_a_real_payment_still_settles_the_booking(self):
        r = self.client.post(
            PUSH, json.dumps({'ReferenceID': self.ref, 'Status': 'true',
                              'Amount': int(self.sr.total_price),
                              'MFSTransactionID': '26797615656'}),
            content_type='application/json',
            HTTP_X_YAS_SECRET=SECRET)
        self.assertEqual(r.status_code, 200)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')
        self.assertEqual(self.sr.payment_transaction_id, '26797615656')

    def test_the_real_payment_is_recorded_even_so(self):
        yas.settle(self.sr, '26797615656', amount=self.sr.total_price)
        row = PaymentTransaction.objects.get(reference='26797615656')
        self.assertFalse(row.is_demo)
        self.assertEqual(row.method, 'yas')
        self.assertEqual(row.amount, self.sr.total_price)
        self.assertEqual(row.client_id, self.sr.client_id)

    def test_the_demo_reference_is_not_released(self):
        # Releasing it would make it claimable again, and the same demo
        # reference could then be presented for a second booking.
        yas.settle(self.sr, '26797615656', amount=self.sr.total_price)
        demo = PaymentTransaction.objects.get(reference=self.demo_ref)
        self.assertEqual(demo.consumed_by_id, self.sr.pk)

    def test_the_released_demo_reference_cannot_book_a_second_job(self):
        yas.settle(self.sr, '26797615656', amount=self.sr.total_price)
        body = {'category': self.cat.id, 'title': 'Second job',
                'description': 'free?', 'location': '9 Secret Street',
                'city': 'Dar', 'workers_needed': 1,
                'duration_type': 'daily',
                'preferred_date': str(timezone.localdate()),
                'preferred_time': '09:00:00',
                'payment_transaction_id': self.demo_ref,
                'payment_method': 'yas'}
        r = post_json(self.client_c,
                      '/api/v1/client/service-requests/create/', body)
        # The project lets the booking be created and leaves it unpaid,
        # rather than refusing it outright. What matters is the money:
        # a reference that has already been used pays for nothing.
        if r.status_code in (200, 201):
            second = ServiceRequest.objects.exclude(pk=self.sr.pk).latest('id')
            self.assertEqual(second.payment_status, 'pending')
            self.assertEqual(second.payment_transaction_id, '')
        # And the original booking keeps its own reference.
        demo = PaymentTransaction.objects.get(reference=self.demo_ref)
        self.assertEqual(demo.consumed_by_id, self.sr.pk)

    def test_the_booking_and_the_row_carry_the_same_receipt(self):
        # The row is unlinked, so this is what puts the two together.
        yas.settle(self.sr, '26830652898', amount=self.sr.total_price)
        self.sr.refresh_from_db()
        row = PaymentTransaction.objects.get(reference='26830652898')
        self.assertEqual(self.sr.payment_transaction_id, row.reference)

    def test_the_same_receipt_twice_leaves_one_row(self):
        yas.settle(self.sr, '26797615656', amount=self.sr.total_price)
        yas.settle(self.sr, '26797615656', amount=self.sr.total_price)
        self.assertEqual(PaymentTransaction.objects.filter(
            reference='26797615656').count(), 1)

    def test_a_w2a_payment_settles_a_live_shaped_booking(self):
        body = xml((("TYPE", "SYNC_BILLPAY_REQUEST"), ("TXNID", "BP7"),
                    ("MSISDN", "0714405395"),
                    ("CUSTOMERREFERENCEID", self.ref),
                    ("AMOUNT", str(int(self.sr.total_price)))))
        r = self.client.post(W2A, body, content_type='text/xml',
                             HTTP_X_YAS_SECRET=SECRET)
        tags = yas.read_command(r.content) or {}
        self.assertEqual(tags.get('RESULT'), 'TS', r.content)
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_status, 'paid')
        self.assertTrue(PaymentTransaction.objects.filter(
            reference='BP7', is_demo=False).exists())
