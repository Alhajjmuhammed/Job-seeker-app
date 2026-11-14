"""Mixx by YAS: regression tests for the money and security fixes.

    python manage.py test tests.test_yas_payments_fixes

Each class is one finding from the review (A-Q). Nothing here reaches
YAS: every outbound call is stubbed exactly as in test_yas_payments,
because their gateway is live and a test that reached it would move real
money.
"""
import logging
import re
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import Client, override_settings
from django.utils import timezone

from accounts.models import User
from clients.models import ClientRefund, PaymentTransaction
from jobs.service_request_models import ServiceRequest
from worker_connect import yas, yas_client
from workers.models import MobileMoneyAccount, WorkerPayout

from .test_full_flows import post_json
from .test_yas_payments import (IDENTIFIED, PAYMENTS_ON, PAYOUTS_ON, PUSH,
                                REFUNDS_ON, SECRET, W2A, YasBase, approver,
                                completed_job, make_payout, make_refund,
                                resmfici, xml)

PAYOUTS = '/api/v1/payments/yas/payouts/'
REFUNDS = '/api/v1/payments/yas/refunds/'


def no_network(*_a, **_k):
    raise AssertionError("A test reached the network")


class FixBase(YasBase):
    """YasBase, with the gateway unreachable unless a test stubs it."""

    def setUp(self):
        super().setUp()
        cache.clear()
        guard = mock.patch.object(yas_client.http_requests, 'post',
                                  side_effect=no_network)
        guard.start()
        self.addCleanup(guard.stop)
        # The worker's own verified wallet: the default payout destination.
        MobileMoneyAccount.objects.create(
            user=self.worker_user, provider='tigo_pesa',
            phone_number='0744555666', account_name='Wor Ker',
            is_default=True, is_verified=True)
        yas_client.forget_token()
        self.addCleanup(yas_client.forget_token)

    def due(self, sr=None):
        return int(yas.shillings_due(sr or self.sr))

    def bill(self, amount=None, txnid='BP1', reference=None):
        return self.tags(self.w2a(xml((
            ("TYPE", "SYNC_BILLPAY_REQUEST"), ("TXNID", txnid),
            ("MSISDN", "0714405395"),
            ("AMOUNT", str(self.due() if amount is None else amount)),
            ("CUSTOMERREFERENCEID", reference or self.ref)))))

    def paid_push(self, receipt='M1', amount=None, reference=None, **extra):
        body = {'ReferenceID': reference or self.ref, 'Status': 'true',
                'MFSTransactionID': receipt,
                'CustomerMSISDN': '255714123456',
                'Amount': self.due() if amount is None else amount}
        body.update(extra)
        return self.push(body)

    def pending(self, sr=None):
        sr = sr or self.sr
        sr.refresh_from_db()
        return sr.payment_status

    def staff(self, name, *perms, superuser=False):
        user = User.objects.create_user(
            username=name, email='%s@t.co' % name, password='x-Pass-12345',
            user_type='admin', is_staff=True, is_superuser=superuser)
        for codename in perms:
            user.user_permissions.add(Permission.objects.get(codename=codename))
        c = Client()
        c.force_login(user)
        return user, c

    def reply(self, payload, code=200):
        resp = mock.Mock(status_code=code, content=b'{}')
        resp.json.return_value = payload
        return resp


# ---------------------------------------------------------------------------
# A. W2A on an already-paid booking
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class A_AlreadyPaidW2ATests(FixBase):
    def test_a_booking_verified_by_hand_is_not_charged_again(self):
        self.sr.mark_payment_verified(self.admin)
        tags = self.bill(txnid='T9')
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(tags['ERRORCODE'], yas.E_LOCKED)
        self.assertFalse(PaymentTransaction.objects.filter(
            reference='T9').exists())

    def test_a_second_transaction_on_a_paid_booking_is_refused(self):
        self.assertEqual(self.bill(txnid='T1')['RESULT'], 'TS')
        tags = self.bill(txnid='T2')
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertFalse(PaymentTransaction.objects.filter(
            reference='T2').exists())

    def test_the_same_txnid_again_is_a_genuine_retry(self):
        self.assertEqual(self.bill(txnid='T1')['RESULT'], 'TS')
        self.assertEqual(self.bill(txnid='T1')['RESULT'], 'TS')
        self.assertEqual(PaymentTransaction.objects.filter(
            reference='T1').count(), 1)

    def test_a_retry_is_answered_ts_even_if_the_price_changed(self):
        # TF to a genuine retry could make YAS reverse money we applied.
        self.bill(txnid='T1')
        ServiceRequest.objects.filter(pk=self.sr.pk).update(
            total_price=D('99999'))
        self.assertEqual(self.bill(txnid='T1', amount=30000)['RESULT'], 'TS')

    def test_a_w2a_without_a_txnid_is_refused(self):
        body = xml((("TYPE", "SYNC_BILLPAY_REQUEST"),
                    ("CUSTOMERREFERENCEID", self.ref),
                    ("AMOUNT", str(self.due()))))
        tags = self.tags(self.w2a(body))
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(self.pending(), 'pending')


# ---------------------------------------------------------------------------
# B. W2A for closed bookings
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class B_ClosedBookingW2ATests(FixBase):
    def test_cancelled_completed_and_refunded_are_locked(self):
        for field, value in (('status', 'cancelled'), ('status', 'completed'),
                             ('payment_status', 'refunded')):
            sr, _ = self.book()
            fields = dict(payment_status='pending', payment_verified=False)
            fields[field] = value
            ServiceRequest.objects.filter(pk=sr.pk).update(**fields)
            ref = sr.ensure_reference()
            tags = self.bill(txnid='X-' + value, reference=ref)
            self.assertEqual(tags['RESULT'], 'TF', value)
            self.assertEqual(tags['ERRORCODE'], yas.E_LOCKED, value)
            sr.refresh_from_db()
            self.assertNotEqual(sr.payment_status, 'paid', value)


# ---------------------------------------------------------------------------
# C. Exact amounts
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class C_ExactAmountTests(FixBase):
    def test_an_overpayment_is_refused_too_high(self):
        tags = self.bill(amount=self.due() * 10)
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(tags['ERRORCODE'], yas.E_TOO_HIGH)
        self.assertEqual(self.pending(), 'pending')

    def test_one_shilling_over_is_still_over(self):
        self.assertEqual(self.bill(amount=self.due() + 1)['ERRORCODE'],
                         yas.E_TOO_HIGH)

    @override_settings(YAS_AMOUNT_TOLERANCE='0.01')
    def test_the_tolerance_only_ever_allows_less(self):
        self.assertEqual(yas.amount_verdict(self.sr, D('29700')), yas.AMOUNT_OK)
        self.assertEqual(yas.amount_verdict(self.sr, D('29699')),
                         yas.AMOUNT_SHORT)
        self.assertEqual(yas.amount_verdict(self.sr, D('30001')),
                         yas.AMOUNT_OVER)

    @override_settings(YAS_AMOUNT_TOLERANCE='5')
    def test_an_absurd_tolerance_falls_back_to_exact(self):
        self.assertEqual(yas.amount_verdict(self.sr, D('1')), yas.AMOUNT_SHORT)


# ---------------------------------------------------------------------------
# D. Push Amount must be present and exact
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class D_PushAmountTests(FixBase):
    def test_zero_negative_missing_or_junk_never_settles(self):
        for i, amount in enumerate(('0', '-5', None, 'abc', [1], 'NaN')):
            sr, _ = self.book()
            ServiceRequest.objects.filter(pk=sr.pk).update(
                payment_status='pending', payment_verified=False)
            ref = sr.ensure_reference()
            body = {'ReferenceID': ref, 'Status': 'success',
                    'MFSTransactionID': 'D%d' % i}
            if amount is not None:
                body['Amount'] = amount
            with self.assertLogs('worker_connect.yas', level='CRITICAL'):
                self.push(body)
            self.assertEqual(self.pending(sr), 'pending', repr(amount))
            row = PaymentTransaction.objects.get(reference='D%d' % i)
            self.assertTrue(row.unapplied_reason, repr(amount))

    def test_overpaid_push_is_not_applied(self):
        with self.assertLogs('worker_connect.yas', level='CRITICAL'):
            self.paid_push(amount=self.due() + 1)
        self.assertEqual(self.pending(), 'pending')

    def test_the_exact_amount_settles(self):
        self.paid_push()
        self.assertEqual(self.pending(), 'paid')
        row = PaymentTransaction.objects.get(reference='M1')
        self.assertEqual(row.unapplied_reason, '')
        self.assertEqual(row.gateway_reference, self.ref)


# ---------------------------------------------------------------------------
# E. Push on paid / closed bookings
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class E_PushOnClosedBookingTests(FixBase):
    def test_a_second_receipt_on_a_paid_booking_is_recorded_and_shouted(self):
        self.paid_push('M1')
        with self.assertLogs('worker_connect.yas', level='CRITICAL') as cm:
            self.paid_push('M2', reference=self.ref + '2027')
        self.assertIn('NOT applied', '\n'.join(cm.output))
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.payment_transaction_id, 'M1')
        row = PaymentTransaction.objects.get(reference='M2')
        self.assertIn('already paid', row.unapplied_reason)
        self.assertEqual(row.service_request_id, self.sr.pk)
        self.assertEqual(row.amount, D(self.due()))

    def test_the_same_receipt_again_stays_quiet(self):
        self.paid_push('M1')
        r = self.paid_push('M1')
        self.assertEqual(r.json()['ResponseDescription'], 'Already settled')
        self.assertEqual(PaymentTransaction.objects.filter(
            reference='M1').count(), 1)

    def test_refunded_cancelled_or_completed_is_never_re_marked_paid(self):
        for field, value in (('payment_status', 'refunded'),
                             ('status', 'cancelled'),
                             ('status', 'completed')):
            sr, _ = self.book()
            fields = dict(payment_status='pending', payment_verified=False)
            fields[field] = value
            ServiceRequest.objects.filter(pk=sr.pk).update(**fields)
            ref = sr.ensure_reference()
            with mock.patch('clients.assignment_mode.apply_assignment_mode'
                            ) as assign:
                with self.assertLogs('worker_connect.yas', level='CRITICAL'):
                    self.paid_push('E-' + value, reference=ref)
            assign.assert_not_called()
            sr.refresh_from_db()
            self.assertNotEqual(sr.payment_status, 'paid', value)
            self.assertEqual(getattr(sr, field), value)
            self.assertTrue(PaymentTransaction.objects.filter(
                reference='E-' + value, service_request=sr).exclude(
                unapplied_reason='').exists(), value)


# ---------------------------------------------------------------------------
# F. pay_service_request: closed bookings and prompt flooding
# ---------------------------------------------------------------------------

@override_settings(**PAYMENTS_ON)
class F_PromptLimitTests(FixBase):
    def url(self, sr=None):
        return '/api/v1/payments/yas/pay/%s/' % (sr or self.sr).id

    def pay(self):
        return post_json(self.client_c, self.url(),
                         {'phone_number': '0714123456'})

    def test_a_second_prompt_inside_the_window_is_refused(self):
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(True, 'ok')) as rp:
            self.assertEqual(self.pay().status_code, 200)
            second = self.pay()
        self.assertEqual(second.status_code, 429)
        self.assertIn('Retry-After', second)
        rp.assert_called_once()

    def test_the_reference_sent_is_stored_with_its_marker(self):
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(True, 'ok')) as rp:
            self.pay()
        sent = rp.call_args.kwargs['reference_id']
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.yas_prompt_reference, sent)
        self.assertTrue(sent.startswith(self.ref) and sent != self.ref)

    def test_after_the_window_a_new_prompt_is_allowed(self):
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(True, 'ok')):
            self.pay()
            ServiceRequest.objects.filter(pk=self.sr.pk).update(
                yas_prompt_sent_at=timezone.now() - timedelta(minutes=10))
            self.assertEqual(self.pay().status_code, 200)

    def test_a_failure_callback_frees_the_window(self):
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(True, 'ok')):
            self.pay()
            self.sr.refresh_from_db()
            self.push({'ReferenceID': self.sr.yas_prompt_reference,
                       'Status': 'failed'})
            self.assertEqual(self.pay().status_code, 200)

    def test_a_prompt_yas_refused_frees_the_window(self):
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(False, '')):
            self.assertEqual(self.pay().status_code, 502)
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(True, 'ok')):
            self.assertEqual(self.pay().status_code, 200)

    def test_a_prompt_that_may_be_ringing_keeps_the_window(self):
        def timed_out(*_a, **kw):
            kw['report']['maybe_sent'] = True
            return False, ''
        with mock.patch.object(yas_client, 'request_payment',
                               side_effect=timed_out):
            self.pay()
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(True, 'ok')):
            self.assertEqual(self.pay().status_code, 429)

    def test_closed_bookings_get_no_prompt(self):
        for field, value in (('status', 'cancelled'), ('status', 'completed'),
                             ('payment_status', 'refunded'),
                             ('payment_verified', True)):
            sr, _ = self.book()
            fields = dict(payment_status='pending', payment_verified=False)
            fields[field] = value
            ServiceRequest.objects.filter(pk=sr.pk).update(**fields)
            with mock.patch.object(yas_client, 'request_payment') as rp:
                r = post_json(self.client_c, self.url(sr),
                              {'phone_number': '0714123456'})
            self.assertEqual(r.status_code, 400, value)
            rp.assert_not_called()


# ---------------------------------------------------------------------------
# G. One receipt, one booking
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class G_ReceiptReuseTests(FixBase):
    def other(self):
        sr, _ = self.book()
        ServiceRequest.objects.filter(pk=sr.pk).update(
            payment_status='pending', payment_verified=False)
        PaymentTransaction.objects.filter(consumed_by=sr).delete()
        return sr, sr.ensure_reference()

    def test_a_push_receipt_cannot_settle_a_second_booking(self):
        self.paid_push('SAME')
        sr, ref = self.other()
        with self.assertLogs('worker_connect.yas', level='CRITICAL'):
            self.paid_push('SAME', reference=ref)
        self.assertEqual(self.pending(sr), 'pending')

    def test_a_w2a_txnid_cannot_settle_a_second_booking(self):
        self.assertEqual(self.bill(txnid='SAME')['RESULT'], 'TS')
        sr, ref = self.other()
        tags = self.bill(txnid='SAME', reference=ref)
        self.assertEqual(tags['RESULT'], 'TF')
        self.assertEqual(tags['ERRORCODE'], yas.E_INVALID)
        self.assertEqual(self.pending(sr), 'pending')


# ---------------------------------------------------------------------------
# H. ensure_reference race
# ---------------------------------------------------------------------------

class H_EnsureReferenceTests(FixBase):
    def test_two_stale_copies_get_the_same_reference(self):
        ServiceRequest.objects.filter(pk=self.sr.pk).update(reference=None)
        first = ServiceRequest.objects.get(pk=self.sr.pk)
        second = ServiceRequest.objects.get(pk=self.sr.pk)
        a = first.ensure_reference()
        b = second.ensure_reference()
        self.assertEqual(a, b)
        self.assertEqual(ServiceRequest.objects.get(pk=self.sr.pk).reference,
                         a)

    def test_an_empty_string_counts_as_none(self):
        ServiceRequest.objects.filter(pk=self.sr.pk).update(reference='')
        sr = ServiceRequest.objects.get(pk=self.sr.pk)
        self.assertRegex(sr.ensure_reference(), r'^WC[A-Z0-9]{8}$')


# ---------------------------------------------------------------------------
# I. Permissions and four-eyes
# ---------------------------------------------------------------------------

class I_PermissionTests(FixBase):
    def test_plain_staff_cannot_create_send_or_resolve(self):
        _u, c = self.staff('helpdesk')
        job = completed_job(self)
        payout = make_payout(self, D('1000'))
        refund = make_refund(self, D('1000'), '0714123456')
        for url, body in (
                (PAYOUTS, {'worker_id': self.wp.id, 'amount': '1000',
                           'service_request_id': job.id}),
                (PAYOUTS + '%s/send/' % payout.id, {}),
                (PAYOUTS + '%s/resolve/' % payout.id,
                 {'outcome': 'paid', 'note': 'statement line 4'}),
                (REFUNDS, {'service_request_id': self.sr.id}),
                (REFUNDS + '%s/send/' % refund.id, {}),
                (REFUNDS + '%s/resolve/' % refund.id,
                 {'outcome': 'paid', 'note': 'statement line 4'})):
            self.assertEqual(post_json(c, url, body).status_code, 403, url)
        # Looking is still fine.
        self.assertEqual(c.get(PAYOUTS).status_code, 200)

    @override_settings(**PAYOUTS_ON)
    def test_the_dedicated_permission_is_enough(self):
        _u, c = self.staff('payroll', 'send_workerpayout')
        payout = make_payout(self, D('1000'))
        with mock.patch.object(yas_client.http_requests, 'post',
                               return_value=mock.Mock(status_code=200,
                                                      text=resmfici('200'))):
            r = post_json(c, PAYOUTS + '%s/send/' % payout.id, {})
        self.assertEqual(r.status_code, 200, r.content)

    @override_settings(**PAYOUTS_ON)
    def test_whoever_approved_it_cannot_send_it(self):
        payout = make_payout(self, D('1000'), created_by=self.admin)
        r = post_json(self.admin_c, PAYOUTS + '%s/send/' % payout.id, {})
        self.assertEqual(r.status_code, 403)
        payout.refresh_from_db()
        self.assertEqual(payout.state, 'pending')

    @override_settings(**PAYOUTS_ON)
    def test_a_payout_nobody_approved_cannot_be_sent(self):
        payout = make_payout(self, D('1000'), created_by=None)
        r = post_json(self.admin_c, PAYOUTS + '%s/send/' % payout.id, {})
        self.assertEqual(r.status_code, 403)

    @override_settings(YAS_REQUIRE_SECOND_APPROVER=False, **PAYOUTS_ON)
    def test_four_eyes_can_be_switched_off(self):
        payout = make_payout(self, D('1000'), created_by=self.admin)
        with mock.patch.object(yas_client.http_requests, 'post',
                               return_value=mock.Mock(status_code=200,
                                                      text=resmfici('200'))):
            r = post_json(self.admin_c, PAYOUTS + '%s/send/' % payout.id, {})
        self.assertEqual(r.status_code, 200)
        payout.refresh_from_db()
        self.assertEqual(payout.sent_by_id, self.admin.id)

    @override_settings(**REFUNDS_ON)
    def test_four_eyes_applies_to_refunds(self):
        refund = make_refund(self, D('1000'), '0714123456',
                             created_by=self.admin)
        r = post_json(self.admin_c, REFUNDS + '%s/send/' % refund.id, {})
        self.assertEqual(r.status_code, 403)

    def test_second_approver_defaults_on(self):
        self.assertTrue(settings.YAS_REQUIRE_SECOND_APPROVER)

    def test_resolving_needs_evidence(self):
        payout = make_payout(self, D('1000'))
        WorkerPayout.objects.filter(pk=payout.pk).update(state='held')
        for note in ('', '   ', 'ok'):
            r = post_json(self.admin_c, PAYOUTS + '%s/resolve/' % payout.id,
                          {'outcome': 'paid', 'note': note})
            self.assertEqual(r.status_code, 400, repr(note))
        payout.refresh_from_db()
        self.assertEqual(payout.state, 'held')


# ---------------------------------------------------------------------------
# J. Payouts tied to earnings
# ---------------------------------------------------------------------------

class J_PayoutEarningsTests(FixBase):
    def create(self, **body):
        return post_json(self.admin_c, PAYOUTS, body)

    def test_a_worker_who_did_not_complete_the_job_is_not_paid(self):
        ServiceRequest.objects.filter(pk=self.sr.pk).update(
            payment_status='paid')
        r = self.create(worker_id=self.wp.id, amount='1000',
                        service_request_id=self.sr.id)
        self.assertEqual(r.status_code, 400)
        self.assertIn('no completed assignment', r.json()['error'])

    def test_a_payout_must_name_a_booking(self):
        r = self.create(worker_id=self.wp.id, amount='1000')
        self.assertEqual(r.status_code, 400)

    def test_no_more_than_was_earned(self):
        job = completed_job(self, pay=D('25000'))
        r = self.create(worker_id=self.wp.id, amount='25001',
                        service_request_id=job.id)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.create(worker_id=self.wp.id, amount='25000',
                                     service_request_id=job.id).status_code,
                         201)

    def test_one_live_payout_per_worker_per_job(self):
        job = completed_job(self)
        self.assertEqual(self.create(worker_id=self.wp.id, amount='1000',
                                     service_request_id=job.id).status_code,
                         201)
        second = self.create(worker_id=self.wp.id, amount='1000',
                             service_request_id=job.id)
        self.assertEqual(second.status_code, 400)
        self.assertIn('already has a payout', second.json()['error'])

    def test_a_failed_payout_can_be_approved_again(self):
        job = completed_job(self)
        first = make_payout(self, D('1000'), service_request=job)
        WorkerPayout.objects.filter(pk=first.pk).update(state='failed')
        make_payout(self, D('1000'), service_request=job)

    def test_the_database_enforces_it_too(self):
        job = completed_job(self)
        make_payout(self, D('1000'), service_request=job)
        with self.assertRaises(IntegrityError), transaction.atomic():
            WorkerPayout.objects.create(
                worker=self.wp, service_request=job, amount=D('1'),
                phone_number='0714123456',
                reference=yas.new_payout_reference())

    def test_the_destination_defaults_to_the_workers_own_number(self):
        MobileMoneyAccount.objects.create(
            user=self.worker_user, provider='tigo_pesa',
            phone_number='0714123456', account_name='Wor Ker',
            is_default=True, is_verified=True)
        payout = make_payout(self, D('1000'))
        self.assertEqual(payout.phone_number, '0714123456')
        self.assertEqual(payout.destination_note, '')

    def test_another_number_needs_a_reason_and_is_recorded(self):
        job = completed_job(self)
        r = self.create(worker_id=self.wp.id, amount='1000',
                        service_request_id=job.id, phone_number='0799000111')
        self.assertEqual(r.status_code, 400)
        self.assertIn('override_reason', r.json()['error'])
        r = self.create(worker_id=self.wp.id, amount='1000',
                        service_request_id=job.id, phone_number='0799000111',
                        override_reason='wallet barred, worker asked by SMS')
        self.assertEqual(r.status_code, 201, r.content)
        payout = WorkerPayout.objects.get(pk=r.json()['id'])
        self.assertEqual(payout.phone_number, '0799000111')
        self.assertIn('wallet barred', payout.destination_note)
        self.assertIn('boss', payout.destination_note)
        self.assertIn('0744555666', payout.destination_note)

    def test_the_same_number_written_differently_is_not_an_override(self):
        job = completed_job(self)
        r = self.create(worker_id=self.wp.id, amount='1000',
                        service_request_id=job.id,
                        phone_number='+255 744 555 666')
        self.assertEqual(r.status_code, 201, r.content)

    @override_settings(YAS_REQUIRE_SECOND_APPROVER=False)
    def test_no_override_without_a_second_approver(self):
        job = completed_job(self)
        r = self.create(worker_id=self.wp.id, amount='1000',
                        service_request_id=job.id, phone_number='0799000111',
                        override_reason='because')
        self.assertEqual(r.status_code, 400)


# ---------------------------------------------------------------------------
# K. Refunds capped at what was paid
# ---------------------------------------------------------------------------

class K_RefundCapTests(FixBase):
    def create(self, **body):
        body.setdefault('service_request_id', self.sr.id)
        return post_json(self.admin_c, REFUNDS, body)

    def test_a_booking_paid_only_by_demo_reference_cannot_be_refunded(self):
        PaymentTransaction.objects.create(
            reference='DEMO-X', client=self.sr.client, amount=D('30000'),
            method='yas', is_demo=True, consumed_by=self.sr)
        self.sr.mark_paid_by_gateway('DEMO-X')
        self.assertEqual(self.create(amount='1000').status_code, 400)

    def test_no_more_than_was_paid(self):
        yas.settle(self.sr, 'R1', amount=D('30000'), gateway_reference=self.ref)
        self.assertEqual(self.create(amount='9999999').status_code, 400)
        self.assertEqual(self.create(amount='20000').status_code, 201)
        self.assertEqual(self.create(amount='10001').status_code, 400)
        self.assertEqual(self.create(amount='10000').status_code, 201)
        self.assertEqual(self.create().status_code, 400)

    def test_a_failed_refund_does_not_count(self):
        yas.settle(self.sr, 'R1', amount=D('30000'), gateway_reference=self.ref)
        first = self.create()
        self.assertEqual(first.status_code, 201)
        ClientRefund.objects.filter(pk=first.json()['id']).update(
            state='failed')
        self.assertEqual(self.create().status_code, 201)

    def test_the_receipt_cannot_be_typed_in(self):
        yas.settle(self.sr, 'R1', amount=D('30000'), gateway_reference=self.ref)
        r = self.create(mfs_transaction_id='SOMEONE-ELSES')
        self.assertEqual(r.status_code, 400)

    @override_settings(**dict(REFUNDS_ON, YAS_BILLER_CODE='EFX'))
    def test_a_refund_names_the_exact_original_reference(self):
        sent = yas_client.reference_for(self.ref, '2026111400000012345678')
        self.paid_push('MFS77', reference=sent)
        self.assertEqual(self.pending(), 'paid')
        refund = make_refund(self, None, '0714123456')
        with mock.patch.object(
                yas_client.http_requests, 'post',
                side_effect=[self.reply({'access_token': 'tok'}),
                             self.reply({'ResponseStatus': True})]) as post:
            r = post_json(self.admin_c, REFUNDS + '%s/send/' % refund.id, {})
        self.assertEqual(r.status_code, 200, r.content)
        body = post.call_args_list[1].kwargs['json']
        self.assertEqual(body['PurchaseReferenceID'], sent)
        self.assertEqual(body['MFSTransactionID'], 'MFS77')
        # The whole payment went back, so the booking reads refunded and
        # can take no more money.
        self.assertEqual(self.pending(), 'refunded')
        self.assertFalse(self.sr.can_take_payment)

    @override_settings(**REFUNDS_ON)
    def test_a_partial_refund_leaves_the_booking_paid(self):
        refund = make_refund(self, D('1000'), '0714123456')
        with mock.patch.object(
                yas_client.http_requests, 'post',
                side_effect=[self.reply({'access_token': 'tok'}),
                             self.reply({'ResponseStatus': True})]):
            post_json(self.admin_c, REFUNDS + '%s/send/' % refund.id, {})
        refund.refresh_from_db()
        self.assertEqual(refund.state, 'paid')
        self.assertEqual(self.pending(), 'paid')

    def test_resolving_a_full_refund_as_paid_marks_the_booking(self):
        refund = make_refund(self, None, '0714123456')
        ClientRefund.objects.filter(pk=refund.pk).update(state='held')
        r = post_json(self.admin_c, REFUNDS + '%s/resolve/' % refund.id,
                      {'outcome': 'paid', 'note': 'on the 14 Nov statement'})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.pending(), 'refunded')

    @override_settings(**IDENTIFIED)
    def test_unapplied_money_can_be_refunded_without_touching_the_booking(self):
        with self.assertLogs('worker_connect.yas', level='CRITICAL'):
            self.paid_push('OVER', amount=self.due() + 500)
        r = self.create()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['amount'], '30500.00')
        refund = ClientRefund.objects.get(pk=r.json()['id'])
        refund.state = 'paid'
        refund.save(update_fields=['state'])
        yas_client.after_refund_paid(refund)
        self.assertEqual(self.pending(), 'pending')


# ---------------------------------------------------------------------------
# L. Timeouts and rows stuck in 'sending'
# ---------------------------------------------------------------------------

@override_settings(**dict(PAYOUTS_ON, **REFUNDS_ON))
class L_TimeoutTests(FixBase):
    def test_money_calls_wait_less_than_gunicorn(self):
        payout = make_payout(self, D('1000'))
        with mock.patch.object(yas_client.http_requests, 'post',
                               return_value=mock.Mock(status_code=200,
                                                      text=resmfici('200'))
                               ) as post:
            yas_client.send_payout(payout)
        self.assertEqual(post.call_args.kwargs['timeout'], 20)

        refund = make_refund(self, D('1000'), '0714123456')
        with mock.patch.object(
                yas_client.http_requests, 'post',
                side_effect=[self.reply({'access_token': 'tok'}),
                             self.reply({'ResponseStatus': True})]) as post:
            yas_client.send_refund(refund)
        token_wait = post.call_args_list[0].kwargs['timeout']
        refund_wait = post.call_args_list[1].kwargs['timeout']
        self.assertLess(token_wait + refund_wait, 30)

    @override_settings(YAS_HTTP_TIMEOUT=60)
    def test_a_long_setting_is_clamped(self):
        self.assertLessEqual(yas_client.http_timeout(), 25)

    def test_gunicorn_still_allows_the_default(self):
        text = (Path(settings.BASE_DIR) / 'gunicorn_config.py').read_text()
        gunicorn = int(re.search(r'^timeout\s*=\s*(\d+)', text, re.M).group(1))
        self.assertLess(yas_client.http_timeout()
                        + yas_client.token_timeout(), gunicorn)

    def test_a_token_wait_never_leaves_a_refund_sending(self):
        refund = make_refund(self, D('1000'), '0714123456')
        with mock.patch.object(yas_client.http_requests, 'post',
                               side_effect=OSError('timed out')):
            state, _ = yas_client.send_refund(refund)
        self.assertEqual(state, 'pending')

    def test_a_row_stuck_sending_can_be_resolved_with_evidence(self):
        payout = make_payout(self, D('1000'))
        WorkerPayout.objects.filter(pk=payout.pk).update(
            state='sending', sent_at=timezone.now() - timedelta(hours=1))
        r = post_json(self.admin_c, PAYOUTS + '%s/resolve/' % payout.id,
                      {'outcome': 'failed'})
        self.assertEqual(r.status_code, 400)
        r = post_json(self.admin_c, PAYOUTS + '%s/resolve/' % payout.id,
                      {'outcome': 'failed', 'note': 'not on the statement'})
        self.assertEqual(r.status_code, 200, r.content)
        payout.refresh_from_db()
        self.assertEqual(payout.state, 'failed')
        self.assertIn('was sending', payout.yas_message)

    def test_a_row_sending_right_now_cannot_be_resolved(self):
        refund = make_refund(self, D('1000'), '0714123456')
        ClientRefund.objects.filter(pk=refund.pk).update(
            state='sending', sent_at=timezone.now())
        r = post_json(self.admin_c, REFUNDS + '%s/resolve/' % refund.id,
                      {'outcome': 'failed', 'note': 'not on the statement'})
        self.assertEqual(r.status_code, 400)

    def test_nothing_retries_a_stuck_row(self):
        payout = make_payout(self, D('1000'))
        WorkerPayout.objects.filter(pk=payout.pk).update(
            state='sending', sent_at=timezone.now() - timedelta(hours=1))
        state, _ = yas_client.send_payout(payout)
        self.assertEqual(state, 'sending')


# ---------------------------------------------------------------------------
# M. Throttling
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class M_ThrottleTests(FixBase):
    def test_real_yas_traffic_is_not_throttled(self):
        codes = set()
        for _ in range(110):
            codes.add(self.push({'ReferenceID': 'WCNOPE0000',
                                 'Status': 'failed'},
                                HTTP_X_REAL_IP='41.222.176.233').status_code)
        self.assertEqual(codes, {200})

    def test_neither_callback_view_has_a_throttle(self):
        self.assertEqual(yas.YasUssdPushCallbackView.throttle_classes, [])
        self.assertEqual(yas.YasBillPaymentView.throttle_classes, [])


# ---------------------------------------------------------------------------
# N. No e-mail floods from anonymous callers
# ---------------------------------------------------------------------------

class _Collect(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class N_LogLevelTests(FixBase):
    def collect(self):
        handler = _Collect()
        log = logging.getLogger('worker_connect.yas')
        log.addHandler(handler)
        self.addCleanup(log.removeHandler, handler)
        return handler

    @override_settings(YAS_CALLBACK_SECRET='', YAS_ALLOWED_IPS='',
                       YAS_BILLER_USERNAME='', YAS_BILLER_PASSWORD='')
    def test_an_unconfigured_endpoint_does_not_mail_admins(self):
        caught = self.collect()
        for _ in range(3):
            self.assertEqual(Client().post(PUSH, data='{}',
                             content_type='application/json').status_code,
                             401)
            Client().post(W2A, data='<COMMAND/>', content_type='text/xml')
        self.assertTrue(caught.records)
        self.assertFalse([r for r in caught.records
                          if r.levelno >= logging.ERROR])

    @override_settings(**IDENTIFIED)
    def test_a_wrong_secret_is_only_a_warning(self):
        caught = self.collect()
        self.push({'ReferenceID': self.ref, 'Status': 'true'},
                  secret='wrong')
        self.assertFalse([r for r in caught.records
                          if r.levelno >= logging.ERROR])


# ---------------------------------------------------------------------------
# O. Non-ASCII secrets
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class O_NonAsciiTests(FixBase):
    def test_a_non_ascii_secret_is_a_401_not_a_500(self):
        c = Client(raise_request_exception=False)
        self.assertEqual(c.post(PUSH, data='{}',
                                content_type='application/json',
                                HTTP_X_YAS_SECRET='caf\xe9').status_code, 401)
        self.assertEqual(c.post(W2A, data='<COMMAND/>',
                                content_type='text/xml',
                                HTTP_X_YAS_SECRET='caf\xe9').status_code, 401)

    @override_settings(YAS_CALLBACK_SECRET='',
                       YAS_BILLER_USERNAME='wc-partner-login',
                       YAS_BILLER_PASSWORD='secret-password')
    def test_a_non_ascii_basic_password_is_a_401(self):
        import base64
        token = base64.b64encode('wc-partner-login:caf\xe9'.encode()).decode()
        c = Client(raise_request_exception=False)
        r = c.post(PUSH, data='{}', content_type='application/json',
                   HTTP_AUTHORIZATION='Basic ' + token)
        self.assertEqual(r.status_code, 401)

    def test_compare_handles_non_ascii_on_both_sides(self):
        self.assertTrue(yas._same('caf\xe9', 'caf\xe9'))
        self.assertFalse(yas._same('caf\xe9', 'cafe'))


# ---------------------------------------------------------------------------
# P. No phone numbers or whole bodies in the log
# ---------------------------------------------------------------------------

@override_settings(**IDENTIFIED)
class P_LogPrivacyTests(FixBase):
    def test_msisdn_is_masked(self):
        self.assertEqual(yas.mask_msisdn('255714123678'), '2557*****678')
        self.assertEqual(yas.mask_msisdn(''), '')

    def test_w2a_does_not_log_the_payers_number(self):
        with self.assertLogs('worker_connect.yas', level='INFO') as cm:
            self.bill()
        written = '\n'.join(cm.output)
        self.assertNotIn('0714405395', written)
        self.assertNotIn('714405395', written)

    def test_push_logs_only_the_fields_it_needs(self):
        with self.assertLogs('worker_connect.yas', level='INFO') as cm:
            self.paid_push(CustomerMSISDN='255714999888',
                           Description='private words')
        written = '\n'.join(cm.output)
        self.assertNotIn('714999888', written)
        self.assertNotIn('private words', written)


# ---------------------------------------------------------------------------
# Q. The YAS log still opens lazily
# ---------------------------------------------------------------------------

class Q_LazyLogTests(FixBase):
    def test_development_handler_is_delayed(self):
        self.assertTrue(settings.LOGGING['handlers']['yas_file']['delay'])

    def test_production_handler_is_delayed(self):
        text = (Path(settings.BASE_DIR) / 'worker_connect'
                / 'settings_production.py').read_text(encoding='utf-8')
        block = text[text.index("'yas_file': {"):]
        block = block[:block.index('}')]
        self.assertIn("'delay': True", block)


# ===========================================================================
# Second review (R1-R7)
# ===========================================================================

def book_with_reference(case, ref):
    """A new booking that quotes ``ref`` as its payment reference."""
    body = {'category': case.cat.id, 'title': 'Free?', 'description': 'x',
            'location': 'x', 'city': 'Dar', 'workers_needed': 1,
            'duration_type': 'daily',
            'preferred_date': str(timezone.localdate()),
            'preferred_time': '09:00:00', 'payment_transaction_id': ref,
            'payment_method': 'yas'}
    r = post_json(case.client_c, '/api/v1/client/service-requests/create/',
                  body)
    case.assertIn(r.status_code, (200, 201), r.content)
    return ServiceRequest.objects.filter(client=case.client_user).latest('id')


@override_settings(**IDENTIFIED)
class R1_ReceiptAsBookingReferenceTests(FixBase):
    def test_an_unapplied_receipt_cannot_pay_a_new_booking(self):
        self.paid_push('M1')
        with self.assertLogs('worker_connect.yas', level='CRITICAL'):
            self.paid_push('M2')
        other = book_with_reference(self, 'M2')
        self.assertNotEqual(other.payment_status, 'paid')
        row = PaymentTransaction.objects.get(reference='M2')
        self.assertIsNone(row.consumed_by_id)

    def test_an_applied_but_unlinked_receipt_cannot_pay_a_new_booking(self):
        sr, _ = self.book()
        ServiceRequest.objects.filter(pk=sr.pk).update(
            payment_status='pending', payment_verified=False)
        self.assertTrue(PaymentTransaction.objects.filter(
            consumed_by=sr).exists())      # the demo slot is held
        self.paid_push('M9', reference=sr.ensure_reference())
        self.assertEqual(self.pending(sr), 'paid')
        other = book_with_reference(self, 'M9')
        self.assertNotEqual(other.payment_status, 'paid')

    def test_redeem_never_returns_a_gateway_row(self):
        self.paid_push('M1')
        self.assertIsNone(PaymentTransaction.redeem('M1', self.client_user))
        self.assertFalse(PaymentTransaction.redeemable().filter(
            reference='M1').exists())


class R2_ResolveFourEyesTests(FixBase):
    def resolve(self, c, url, outcome='failed'):
        return post_json(c, url, {'outcome': outcome,
                                  'note': 'checked the statement'})

    def test_the_approver_cannot_resolve_their_own_refund(self):
        refund = make_refund(self, None, '', created_by=self.admin)
        ClientRefund.objects.filter(pk=refund.pk).update(state='held')
        r = self.resolve(self.admin_c, REFUNDS + '%s/resolve/' % refund.id)
        self.assertEqual(r.status_code, 403)
        refund.refresh_from_db()
        self.assertEqual(refund.state, 'held')
        # So no second full refund can be approved behind it.
        with self.assertRaises(yas_client.RefundRefused):
            yas_client.create_refund(self.sr, None, '', created_by=self.admin)

    def test_the_sender_cannot_resolve_it_either(self):
        refund = make_refund(self, None, '')
        ClientRefund.objects.filter(pk=refund.pk).update(
            state='held', sent_by=self.admin)
        r = self.resolve(self.admin_c, REFUNDS + '%s/resolve/' % refund.id)
        self.assertEqual(r.status_code, 403)

    def test_a_third_person_can(self):
        refund = make_refund(self, None, '')
        ClientRefund.objects.filter(pk=refund.pk).update(state='held')
        r = self.resolve(self.admin_c, REFUNDS + '%s/resolve/' % refund.id)
        self.assertEqual(r.status_code, 200, r.content)

    def test_the_approver_cannot_resolve_their_own_payout(self):
        payout = make_payout(self, D('1000'), created_by=self.admin)
        WorkerPayout.objects.filter(pk=payout.pk).update(state='held')
        r = self.resolve(self.admin_c, PAYOUTS + '%s/resolve/' % payout.id,
                         'paid')
        self.assertEqual(r.status_code, 403)


class R3_RefundDestinationTests(FixBase):
    @override_settings(**IDENTIFIED)
    def test_w2a_records_the_paying_wallet(self):
        self.bill(txnid='BPW')
        self.assertEqual(PaymentTransaction.objects.get(
            reference='BPW').payer_msisdn, '255714405395')

    @override_settings(**IDENTIFIED)
    def test_push_records_the_reported_wallet(self):
        self.paid_push('MP', CustomerMSISDN='0714999888')
        self.assertEqual(PaymentTransaction.objects.get(
            reference='MP').payer_msisdn, '255714999888')

    def test_push_uses_the_prompted_number_only_for_that_prompt(self):
        sent = yas_client.reference_for(self.ref, '2026111400000011111111')
        ServiceRequest.objects.filter(pk=self.sr.pk).update(
            yas_prompt_reference=sent, yas_prompt_msisdn='255714777666')
        self.sr.refresh_from_db()
        self.assertEqual(yas._push_payer(self.sr, sent, ''), '255714777666')
        self.assertEqual(yas._push_payer(self.sr, self.ref + '99', ''), '')

    @override_settings(**PAYMENTS_ON)
    def test_the_pay_endpoint_stores_the_prompted_number(self):
        with mock.patch.object(yas_client, 'request_payment',
                               return_value=(True, 'ok')):
            post_json(self.client_c, '/api/v1/payments/yas/pay/%s/'
                      % self.sr.id, {'phone_number': '0714777666'})
        self.sr.refresh_from_db()
        self.assertEqual(self.sr.yas_prompt_msisdn, '255714777666')

    def settle_from(self, payer=''):
        yas.settle(self.sr, 'RP1', amount=D('30000'),
                   gateway_reference=self.ref, payer_msisdn=payer)

    def test_a_refund_goes_back_to_the_paying_wallet_by_default(self):
        self.settle_from('255714405395')
        r = post_json(self.admin_c, REFUNDS,
                      {'service_request_id': self.sr.id})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['phone_number'], '255714405395')
        self.assertEqual(r.json()['destination_note'], '')

    def test_another_number_needs_a_reason_and_is_recorded(self):
        self.settle_from('255714405395')
        r = post_json(self.admin_c, REFUNDS, {
            'service_request_id': self.sr.id, 'phone_number': '0799000111'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('override_reason', r.json()['error'])
        r = post_json(self.admin_c, REFUNDS, {
            'service_request_id': self.sr.id, 'phone_number': '0799000111',
            'override_reason': 'payer wallet closed, client asked in writing'})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIn('wallet closed', r.json()['destination_note'])
        self.assertIn('boss', r.json()['destination_note'])

    @override_settings(YAS_REQUIRE_SECOND_APPROVER=False)
    def test_no_override_without_a_second_approver(self):
        self.settle_from('255714405395')
        r = post_json(self.admin_c, REFUNDS, {
            'service_request_id': self.sr.id, 'phone_number': '0799000111',
            'override_reason': 'because'})
        self.assertEqual(r.status_code, 400)

    def test_an_unknown_payer_falls_back_to_the_profile_and_says_so(self):
        self.settle_from('')
        r = post_json(self.admin_c, REFUNDS,
                      {'service_request_id': self.sr.id})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['phone_number'], '+255711222333')
        self.assertIn('not reported', r.json()['destination_note'])


class R4_PayoutNeedsAPaidBookingTests(FixBase):
    def test_unpaid_or_refunded_bookings_pay_no_worker(self):
        for state in ('pending', 'refunded'):
            job = completed_job(self)
            ServiceRequest.objects.filter(pk=job.pk).update(
                payment_status=state, payment_verified=False)
            with self.assertRaises(yas_client.PayoutRefused):
                make_payout(self, D('1000'), service_request=job)


class R5_VerifiedWalletTests(FixBase):
    def test_an_unverified_wallet_is_not_the_default_destination(self):
        MobileMoneyAccount.objects.all().delete()
        MobileMoneyAccount.objects.create(
            user=self.worker_user, provider='tigo_pesa',
            phone_number='0799123123', account_name='Not checked',
            is_default=True, is_verified=False)
        self.assertEqual(yas_client.registered_number(self.wp), '')
        # Nor the editable account phone: an explicit override is needed.
        with self.assertRaises(yas_client.PayoutRefused):
            yas_client.create_payout(self.wp, D('1000'), created_by=self.admin,
                                     service_request=completed_job(self))
        payout = yas_client.create_payout(
            self.wp, D('1000'), created_by=self.admin,
            service_request=completed_job(self), phone_number='0744555666',
            override_reason='checked by phone call with the worker')
        self.assertIn('checked by phone call', payout.destination_note)

    def test_editing_a_verified_wallet_unverifies_it(self):
        wallet = MobileMoneyAccount.objects.get(user=self.worker_user)
        wallet.phone_number = '0799999999'
        wallet.save()
        wallet.refresh_from_db()
        self.assertFalse(wallet.is_verified)
        self.assertIsNone(wallet.verified_at)
        self.assertEqual(yas_client.registered_number(self.wp), '')

    def test_changing_the_network_unverifies_it_too(self):
        wallet = MobileMoneyAccount.objects.get(user=self.worker_user)
        wallet.provider = 'mpesa'
        wallet.save(update_fields=['provider'])
        wallet.refresh_from_db()
        self.assertFalse(wallet.is_verified)

    def test_other_edits_keep_it_verified(self):
        wallet = MobileMoneyAccount.objects.get(user=self.worker_user)
        wallet.account_name = 'New name'
        wallet.save()
        wallet.refresh_from_db()
        self.assertTrue(wallet.is_verified)

    def test_the_admin_cannot_edit_a_verified_wallets_number(self):
        from django.contrib.admin.sites import site
        wallet = MobileMoneyAccount.objects.get(user=self.worker_user)
        admin_ = site._registry[MobileMoneyAccount]
        fields = admin_.get_readonly_fields(None, wallet)
        self.assertIn('phone_number', fields)
        self.assertIn('provider', fields)

    def test_the_api_edit_of_a_verified_wallet_unverifies_it(self):
        wallet = MobileMoneyAccount.objects.get(user=self.worker_user)
        r = self.worker_c.patch(
            '/api/v1/payment-methods/mobile-money/%s/' % wallet.id,
            data='{"phone_number": "0799999999"}',
            content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        wallet.refresh_from_db()
        self.assertEqual(wallet.phone_number, '0799999999')
        self.assertFalse(wallet.is_verified)
        self.assertEqual(yas_client.registered_number(self.wp), '')

    # -- the Django admin path (staff without money rights) ---------------------------
    def staff_without_money_rights(self):
        u = User.objects.create_user(email='desk@t.co', username='helpdesk', password='x-Pass-2026!',
                                     user_type='admin', is_staff=True)
        u.user_permissions.add(*Permission.objects.filter(
            codename__in=['add_mobilemoneyaccount', 'change_mobilemoneyaccount', 'view_mobilemoneyaccount']))
        c = Client(); c.force_login(u)
        return u, c

    def test_handing_a_verified_wallet_to_someone_else_unverifies_it(self):
        other = User.objects.create_user(email='o2@t.co', username='otherguy', password='x-Pass-2026!', user_type='worker')
        mine = MobileMoneyAccount.objects.create(user=other, provider='tigo_pesa', phone_number='0714222222',
                                                 is_verified=True, is_default=True)
        mine.user = self.worker_user
        mine.save()
        mine.refresh_from_db()
        self.assertFalse(mine.is_verified)

    def test_helpdesk_staff_cannot_verify_or_reassign_wallets_in_admin(self):
        from django.contrib.admin.sites import site
        from django.test import RequestFactory
        u, c = self.staff_without_money_rights()
        admin_ = site._registry[MobileMoneyAccount]
        req = RequestFactory().get('/'); req.user = u
        wallet = MobileMoneyAccount.objects.get(user=self.worker_user)
        ro = admin_.get_readonly_fields(req, wallet)
        self.assertIn('user', ro)          # a verified wallet's owner is locked
        self.assertIn('is_verified', ro)   # and only money people may tick "verified"
        self.assertIn('is_verified', admin_.get_readonly_fields(req, None))
        self.assertNotIn('verify_accounts', admin_.get_actions(req))
        # ticking is_verified on a new wallet through the admin form does nothing for them
        r = c.post('/admin/workers/mobilemoneyaccount/add/', {
            'user': self.worker_user.id, 'provider': 'tigo_pesa', 'phone_number': '0714333333',
            'account_name': 'x', 'is_verified': 'on', 'is_default': 'on', 'is_active': 'on'})
        self.assertIn(r.status_code, (200, 302))
        added = MobileMoneyAccount.objects.filter(phone_number='0714333333').first()
        if added is not None:
            self.assertFalse(added.is_verified)
        # and the bulk "verify" action is refused
        fresh = MobileMoneyAccount.objects.create(user=self.worker_user, provider='tigo_pesa', phone_number='0714444444')
        c.post('/admin/workers/mobilemoneyaccount/', {'action': 'verify_accounts', '_selected_action': [fresh.id]})
        fresh.refresh_from_db()
        self.assertFalse(fresh.is_verified)

    def test_money_superuser_can_verify_and_it_is_logged(self):
        from django.contrib.admin.models import LogEntry
        boss = User.objects.create_superuser(email='boss2@t.co', username='boss2', password='x-Pass-2026!')
        c = Client(); c.force_login(boss)
        fresh = MobileMoneyAccount.objects.create(user=self.worker_user, provider='tigo_pesa', phone_number='0714555555')
        c.post('/admin/workers/mobilemoneyaccount/', {'action': 'verify_accounts', '_selected_action': [fresh.id]})
        fresh.refresh_from_db()
        self.assertTrue(fresh.is_verified)
        self.assertIsNotNone(fresh.verified_at)
        self.assertTrue(LogEntry.objects.filter(user=boss, object_id=str(fresh.id)).exists())


@override_settings(**IDENTIFIED)
class R6_UnconfirmedAmountTests(FixBase):
    def unconfirmed(self):
        with self.assertLogs('worker_connect.yas', level='CRITICAL'):
            self.push({'ReferenceID': self.ref, 'Status': 'true',
                       'MFSTransactionID': 'NOAMT'})
        row = PaymentTransaction.objects.get(reference='NOAMT')
        self.assertFalse(row.amount_confirmed)
        return row

    def confirm(self, row, c=None, **body):
        body.setdefault('amount', '25000')
        body.setdefault('note', 'statement 14 Nov line 3')
        return post_json(c or self.admin_c, '/api/v1/payments/yas/payments/'
                         '%s/confirm-amount/' % row.id, body)

    def test_it_is_not_refundable_until_confirmed(self):
        self.unconfirmed()
        r = post_json(self.admin_c, REFUNDS,
                      {'service_request_id': self.sr.id})
        self.assertEqual(r.status_code, 400)
        self.assertIn('Confirm the amount', r.json()['error'])
        self.assertEqual(yas_client._refunded_against(
            yas_client.gateway_payments(self.sr, refundable_only=True)), 0)

    def test_a_confirmed_amount_becomes_the_cap(self):
        row = self.unconfirmed()
        self.assertEqual(self.confirm(row).status_code, 200)
        row.refresh_from_db()
        self.assertTrue(row.amount_confirmed)
        self.assertEqual(row.amount, D('25000'))
        self.assertEqual(row.amount_confirmed_by_id, self.admin.id)
        # The confirmer may not approve its refund; somebody else may.
        with self.assertRaises(yas_client.RefundRefused):
            yas_client.create_refund(self.sr, None, '', created_by=self.admin)
        refund = yas_client.create_refund(self.sr, None, '',
                                          created_by=approver())
        self.assertEqual(refund.amount, D('25000'))

    def test_confirming_needs_evidence_and_permission(self):
        row = self.unconfirmed()
        self.assertEqual(self.confirm(row, note='').status_code, 400)
        _u, staff = self.staff('helpdesk2')
        self.assertEqual(self.confirm(row, c=staff).status_code, 403)
        self.assertEqual(self.confirm(row).status_code, 200)
        self.assertEqual(self.confirm(row).status_code, 400)  # only once

    def test_a_confirmed_amount_cannot_exceed_what_we_asked_for(self):
        row = self.unconfirmed()
        for amount in ('9000000', '30001', '0', '-5', '0.5'):
            self.assertEqual(self.confirm(row, amount=amount).status_code,
                             400, amount)
        self.assertEqual(self.confirm(row, amount='30000').status_code, 200)

    @override_settings(**REFUNDS_ON)
    def test_the_confirmer_may_not_send_or_resolve_its_refund(self):
        row = self.unconfirmed()
        self.confirm(row)
        refund = yas_client.create_refund(self.sr, None, '',
                                          created_by=approver())
        r = post_json(self.admin_c, REFUNDS + '%s/send/' % refund.id, {})
        self.assertEqual(r.status_code, 403)
        ClientRefund.objects.filter(pk=refund.pk).update(state='held')
        r = post_json(self.admin_c, REFUNDS + '%s/resolve/' % refund.id,
                      {'outcome': 'failed', 'note': 'checked the statement'})
        self.assertEqual(r.status_code, 403)


@override_settings(**dict(PAYOUTS_ON, **REFUNDS_ON))
class R7_SendTimeRecheckTests(FixBase):
    def test_a_payout_whose_booking_was_refunded_is_not_sent(self):
        payout = make_payout(self, D('1000'))
        ServiceRequest.objects.filter(pk=payout.service_request_id).update(
            payment_status='refunded')
        state, message = yas_client.send_payout(payout)   # network guarded
        self.assertEqual(state, 'pending')
        self.assertIn('refunded', message)

    def test_a_payout_over_the_cap_from_older_rules_is_not_sent(self):
        payout = make_payout(self, D('1000'))
        WorkerPayout.objects.filter(pk=payout.pk).update(amount=D('99999'))
        payout.refresh_from_db()
        state, message = yas_client.send_payout(payout)
        self.assertEqual(state, 'pending')
        self.assertIn('more than', message)

    def test_a_payout_with_no_completed_job_is_not_sent(self):
        from jobs.service_request_models import ServiceRequestAssignment
        payout = make_payout(self, D('1000'))
        ServiceRequestAssignment.objects.filter(
            service_request=payout.service_request).update(status='accepted')
        state, _ = yas_client.send_payout(payout)
        self.assertEqual(state, 'pending')

    def test_a_refund_not_linked_to_a_yas_payment_is_not_sent(self):
        legacy = ClientRefund.objects.create(
            service_request=self.sr, client=self.sr.client,
            amount=D('9999999'), phone_number='0714123456',
            reference=yas.new_refund_reference(),
            mfs_transaction_id='X', purchase_reference=self.ref)
        with mock.patch.object(yas_client, 'token', return_value='tok'):
            state, message = yas_client.send_refund(legacy)
        self.assertEqual(state, 'pending')
        self.assertIn('not linked', message)

    def test_a_refund_over_the_cap_is_not_sent(self):
        refund = make_refund(self, D('1000'), '')
        ClientRefund.objects.filter(pk=refund.pk).update(amount=D('99999'))
        refund.refresh_from_db()
        with mock.patch.object(yas_client, 'token', return_value='tok'):
            state, message = yas_client.send_refund(refund)
        self.assertEqual(state, 'pending')
        self.assertIn('more than', message)

    def test_a_refund_of_an_unconfirmed_payment_is_not_sent(self):
        refund = make_refund(self, D('1000'), '')
        PaymentTransaction.objects.filter(pk=refund.payment_id).update(
            amount_confirmed=False)
        with mock.patch.object(yas_client, 'token', return_value='tok'):
            state, _ = yas_client.send_refund(refund)
        self.assertEqual(state, 'pending')
