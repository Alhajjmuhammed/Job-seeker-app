"""
End-to-end checks of every main flow, as real HTTP requests on a throwaway
database: login (website and app), registration, booking, payment proof and
admin verification, assignment, clock in/out, completion and earnings, and
the privacy rules around documents, search and messaging.

    python manage.py test tests.test_full_flows
"""
import json
import shutil
import tempfile
from decimal import Decimal as D

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from agents.models import AgentProfile
from clients.models import ClientProfile, PaymentTransaction
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
from jobs.models import Message
from workers.models import Category, WorkerDocument, WorkerProfile

PW = 'Str0ng-pass-2026'
MEDIA = tempfile.mkdtemp(prefix='wc-test-media-')

# smallest valid PNG, for upload validation
PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f'
       b'\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00'
       b'IEND\xaeB`\x82')


def post_json(client, url, data=None, **extra):
    return client.post(url, json.dumps(data or {}), content_type='application/json', **extra)


def patch_json(client, url, data=None):
    return client.patch(url, json.dumps(data or {}), content_type='application/json')


def patch_file(client, url, field, upload):
    from django.test.client import encode_multipart, BOUNDARY, MULTIPART_CONTENT
    return client.patch(url, encode_multipart(BOUNDARY, {field: upload}), content_type=MULTIPART_CONTENT)


@override_settings(MEDIA_ROOT=MEDIA)
class FlowBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name='Plumber', daily_rate=D('25000'), service_fee=D('5000'))
        cls.admin = User.objects.create_user(
            email='admin@t.co', username='boss', password=PW,
            user_type='admin', is_staff=True, is_superuser=True)
        cls.client_user = User.objects.create_user(
            email='Client.One@t.co', username='clientone', password=PW, user_type='client',
            first_name='Cli', last_name='One', phone_number='+255711222333')
        ClientProfile.objects.create(user=cls.client_user)
        cls.other_client = User.objects.create_user(
            email='other@t.co', username='otherclient', password=PW, user_type='client',
            first_name='Oth', last_name='Er')
        ClientProfile.objects.create(user=cls.other_client)
        cls.agent_user = User.objects.create_user(
            email='agent@t.co', username='agentx', password=PW, user_type='agent')
        cls.agent = AgentProfile.objects.create(user=cls.agent_user, is_verified=True,
                                                commission_rate=D('10'))
        cls.worker_user = User.objects.create_user(
            email='worker@t.co', username='workerw', password=PW, user_type='worker',
            first_name='Wor', last_name='Ker', phone_number='0744555666')
        cls.wp = WorkerProfile.objects.create(
            user=cls.worker_user, verification_status='verified', availability='available',
            is_public=True, city='Dar', agent=cls.agent)
        cls.wp.categories.add(cls.cat)
        cls.worker2_user = User.objects.create_user(
            email='worker2@t.co', username='workertwo', password=PW, user_type='worker',
            first_name='Two', last_name='Worker')
        cls.wp2 = WorkerProfile.objects.create(
            user=cls.worker2_user, verification_status='verified', availability='available',
            is_public=True, city='Dar')
        cls.wp2.categories.add(cls.cat)

    def setUp(self):
        cache.clear()
        self.admin_c, self.client_c, self.worker_c = Client(), Client(), Client()
        self.admin_c.force_login(self.admin)
        self.client_c.force_login(self.client_user)
        self.worker_c.force_login(self.worker_user)

    # -- helpers -------------------------------------------------------------
    def book(self, workers=1, **extra):
        """Client takes a (demo) payment reference and books with it."""
        total = float(self.cat.daily_rate * workers + self.cat.service_fee)
        pay = post_json(self.client_c, '/api/v1/client/process-payment/',
                        {'amount': total, 'payment_type': 'yas', 'phone_number': '+255711222333'})
        self.assertEqual(pay.status_code, 200, pay.content)
        ref = pay.json()['transaction_id']
        body = {'category': self.cat.id, 'title': 'Leaky tap', 'description': 'fix it',
                'location': '12 Secret Street', 'city': 'Dar', 'workers_needed': workers,
                'duration_type': 'daily', 'preferred_date': str(timezone.now().date()),
                'preferred_time': '09:00:00', 'payment_transaction_id': ref,
                'payment_method': 'yas', **extra}
        r = post_json(self.client_c, '/api/v1/client/service-requests/create/', body)
        self.assertIn(r.status_code, (200, 201), r.content)
        return ServiceRequest.objects.filter(client=self.client_user).latest('id'), ref

    def assign_and_accept(self, sr, worker_c=None, wp=None):
        wp = wp or self.wp
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': wp.id})
        self.assertIn(r.status_code, (200, 201), r.content)
        asg = ServiceRequestAssignment.objects.get(service_request=sr, worker=wp)
        r = post_json(worker_c or self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/respond/',
                      {'accepted': True})
        self.assertEqual(r.status_code, 200, r.content)
        asg.refresh_from_db()
        return asg


class LoginTests(FlowBase):
    def api_login(self, identifier, password=PW):
        return post_json(Client(), '/api/auth/login/', {'email': identifier, 'password': password})

    def test_app_login_with_every_identifier(self):
        for ident in ['Client.One@t.co', 'client.one@T.CO', 'clientone', 'CLIENTONE',
                      '+255711222333', '0711222333', '255711222333', '711 222 333']:
            r = self.api_login(ident)
            self.assertEqual(r.status_code, 200, f'{ident}: {r.content}')
            self.assertEqual(r.json()['user']['email'], 'Client.One@t.co')
            self.assertTrue(r.json()['token'])

    def test_app_login_rejects_wrong_details(self):
        self.assertEqual(self.api_login('clientone', 'wrong').status_code, 401)
        self.assertEqual(self.api_login('nobody').status_code, 401)
        self.assertEqual(post_json(Client(), '/api/auth/login/', {'password': PW}).status_code, 400)

    def test_shared_phone_uses_password_to_pick_account(self):
        u = User.objects.create_user(email='twin@t.co', username='twin', password='Other-pass-99',
                                     user_type='worker', phone_number='0711 222 333')
        r = self.api_login('0711222333', 'Other-pass-99')
        self.assertEqual(r.json()['user']['email'], u.email)
        u.set_password(PW)
        u.save()
        r = self.api_login('0711222333', PW)
        self.assertEqual(r.status_code, 401)
        self.assertIn('email or username', r.json()['message'])

    def test_website_login_with_every_identifier(self):
        for ident in ['client.one@t.co', 'clientone', '0711222333']:
            c = Client()
            r = c.post('/accounts/login/', {'username': ident, 'password': PW})
            self.assertEqual(r.status_code, 302, ident)
            self.assertIn('/clients/', r['Location'], ident)

    def test_website_login_lockout_after_repeated_failures(self):
        c = Client()
        for _ in range(10):
            c.post('/accounts/login/', {'username': 'clientone', 'password': 'bad'}, HTTP_X_REAL_IP='1.2.3.4')
        r = c.post('/accounts/login/', {'username': 'clientone', 'password': PW}, HTTP_X_REAL_IP='1.2.3.4')
        self.assertEqual(r.status_code, 429)
        # a different address is unaffected
        r = Client().post('/accounts/login/', {'username': 'clientone', 'password': PW}, HTTP_X_REAL_IP='5.6.7.8')
        self.assertEqual(r.status_code, 302)

    def test_login_next_cannot_redirect_off_site(self):
        u = User.objects.create_user(email='plain@t.co', username='plain', password=PW, user_type='')
        r = Client().post('/accounts/login/?next=https://evil.example/', {'username': 'plain', 'password': PW})
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('evil.example', r['Location'])
        self.assertTrue(u)

    def test_registration_rejects_email_differing_only_by_case(self):
        r = post_json(Client(), '/api/auth/register/', {
            'firstName': 'A', 'lastName': 'B', 'email': 'CLIENT.ONE@t.co', 'phone': '0700000001',
            'password': PW, 'userType': 'client'})
        self.assertEqual(r.status_code, 400, r.content)

    def test_app_registration_then_login(self):
        r = post_json(Client(), '/api/auth/register/', {
            'firstName': 'New', 'lastName': 'Worker', 'email': 'New.Worker@t.co', 'phone': '0755123456',
            'password': PW, 'userType': 'worker', 'workerType': 'non-academic'})
        self.assertIn(r.status_code, (200, 201), r.content)
        self.assertEqual(self.api_login('0755123456').status_code, 200)
        self.assertEqual(self.api_login('new.worker@t.co').status_code, 200)

    def test_password_reset_link_points_at_website(self):
        from django.core import mail
        post_json(Client(), '/api/auth/password-reset/', {'email': 'client.one@t.co'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/accounts/reset-password/', mail.outbox[0].body)
        self.assertNotIn('localhost:8081', mail.outbox[0].body)


class BookingAndPaymentTests(FlowBase):
    def test_payment_endpoint_needs_no_card_details_and_is_pending(self):
        r = post_json(self.client_c, '/api/v1/client/process-payment/', {'amount': 30000, 'payment_type': 'card'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'pending_verification')

    def test_demo_reference_books_but_is_not_paid_until_admin_verifies(self):
        sr, ref = self.book()
        self.assertEqual(sr.payment_status, 'pending')
        self.assertEqual(sr.payment_transaction_id, ref)
        self.assertEqual(sr.total_price, D('30000'))

        # proof upload, then admin verification marks it paid
        r = patch_file(self.client_c, f'/api/v1/clients/requests/{sr.id}/update/',
                       'payment_screenshot', SimpleUploadedFile('p.png', PNG, 'image/png'))
        self.assertEqual(r.status_code, 200, r.content)
        r = self.admin_c.post(f'/dashboard/service-requests/{sr.id}/verify-payment/')
        self.assertEqual(r.status_code, 302)
        sr.refresh_from_db()
        self.assertEqual(sr.payment_status, 'paid')
        self.assertTrue(sr.payment_verified)

        # a verified proof can no longer be swapped
        r = patch_file(self.client_c, f'/api/v1/clients/requests/{sr.id}/update/',
                       'payment_screenshot', SimpleUploadedFile('q.png', PNG, 'image/png'))
        self.assertEqual(r.status_code, 400)

    def test_reference_cannot_be_used_twice_or_for_another_amount(self):
        sr, ref = self.book()
        body = {'category': self.cat.id, 'title': 'Again', 'description': 'x', 'location': 'x', 'city': 'Dar',
                'workers_needed': 1, 'duration_type': 'daily', 'preferred_date': str(timezone.now().date()),
                'preferred_time': '09:00:00', 'payment_transaction_id': ref, 'payment_method': 'yas'}
        post_json(self.client_c, '/api/v1/client/service-requests/create/', body)
        second = ServiceRequest.objects.filter(client=self.client_user).latest('id')
        self.assertNotEqual(second.id, sr.id)
        self.assertEqual(second.payment_transaction_id, '')
        self.assertEqual(PaymentTransaction.objects.get(reference=ref).consumed_by_id, sr.id)

    def test_auto_assign_waits_for_verified_payment(self):
        sr, _ = self.book(assignment_mode='auto_nearest', latitude=-6.8, longitude=39.28)
        self.wp.latitude, self.wp.longitude = -6.81, 39.29
        self.wp.save()
        self.assertFalse(sr.assignments.exists())
        sr.payment_screenshot = SimpleUploadedFile('p.png', PNG, 'image/png')
        sr.save()
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/verify-payment/')
        sr.refresh_from_db()
        if sr.assignment_mode == 'auto_nearest':  # coordinates were accepted
            self.assertTrue(sr.assignments.exists())

    def test_client_cannot_change_workers_after_payment(self):
        sr, _ = self.book()
        url = f'/api/v1/clients/requests/{sr.id}/update/'
        self.assertEqual(patch_json(self.client_c, url, {'workers_needed': 'abc'}).status_code, 400)
        self.assertEqual(patch_json(self.client_c, url, {'workers_needed': -3}).status_code, 400)
        # unpaid: allowed, and the price follows
        self.assertEqual(patch_json(self.client_c, url, {'workers_needed': 2}).status_code, 200)
        sr.refresh_from_db()
        self.assertEqual(sr.total_price, D('55000'))
        # paid: refused
        ServiceRequest.objects.filter(pk=sr.pk).update(payment_status='paid')
        self.assertEqual(patch_json(self.client_c, url, {'workers_needed': 5}).status_code, 400)
        r = self.client_c.put(f'/api/v1/client/service-requests/{sr.id}/update/',
                              json.dumps({'workers_needed': 5}), content_type='application/json')
        self.assertEqual(r.status_code, 400, r.content)

    def test_other_client_cannot_see_or_edit_my_request(self):
        sr, _ = self.book()
        other = Client()
        other.force_login(self.other_client)
        self.assertEqual(other.get(f'/api/v1/clients/requests/{sr.id}/').status_code, 404)
        self.assertEqual(patch_json(other, f'/api/v1/clients/requests/{sr.id}/update/',
                                    {'title': 'hacked'}).status_code, 404)


class WorkFlowTests(FlowBase):
    def test_full_job_and_earnings_credited_once(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        self.assertEqual(asg.status, 'accepted')
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.availability, 'busy')

        base = f'/api/v1/worker/my-assignments/{asg.id}'
        self.assertEqual(post_json(self.worker_c, f'{base}/clock-in/').status_code, 200)
        # cannot complete while clocked in
        self.assertEqual(post_json(self.worker_c, f'{base}/complete/').status_code, 400)
        self.assertEqual(post_json(self.worker_c, f'{base}/clock-out/').status_code, 200)
        r = post_json(self.worker_c, f'{base}/complete/', {'completion_notes': 'done'})
        self.assertEqual(r.status_code, 200, r.content)

        self.wp.refresh_from_db()
        self.agent.refresh_from_db()
        self.assertEqual(self.wp.total_earnings, D('25000'))
        self.assertEqual(self.wp.completed_jobs, 1)
        self.assertEqual(self.wp.availability, 'available')
        self.assertEqual(self.agent.total_commission_earned, D('2500.00'))
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'completed')

        # every other completion route refuses to pay again
        self.assertEqual(post_json(self.worker_c, f'{base}/complete/').status_code, 400)
        self.assertEqual(self.worker_c.patch(f'/api/v1/workers/assigned-jobs/{sr.id}/status/',
                                             json.dumps({'status': 'completed'}),
                                             content_type='application/json').status_code, 400)
        self.assertEqual(post_json(self.worker_c, f'/api/v1/worker/service-requests/{asg.id}/complete/').status_code, 400)
        self.wp.refresh_from_db()
        self.agent.refresh_from_db()
        self.assertEqual(self.wp.total_earnings, D('25000'))
        self.assertEqual(self.wp.completed_jobs, 1)
        self.assertEqual(self.agent.total_commission_earned, D('2500.00'))

    def test_rejected_or_unaccepted_assignment_cannot_be_completed(self):
        sr, _ = self.book()
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        asg = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp)
        # not accepted yet
        self.assertEqual(post_json(self.worker_c, f'/api/v1/worker/service-requests/{asg.id}/complete/').status_code, 400)
        post_json(self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/respond/',
                  {'accepted': False, 'rejection_reason': 'busy'})
        self.assertEqual(post_json(self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/complete/').status_code, 400)
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.total_earnings, D('0'))

    def test_busy_worker_cannot_be_assigned_again(self):
        sr1, _ = self.book()
        self.assign_and_accept(sr1)
        sr2, _ = self.book()
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr2.id}/assign/', {'worker_id': self.wp.id})
        self.assertEqual(r.status_code, 400)

    def test_client_mark_finished_pays_each_worker_once(self):
        sr, _ = self.book(workers=2)
        self.assign_and_accept(sr)
        w2 = Client()
        w2.force_login(self.worker2_user)
        self.assign_and_accept(sr, worker_c=w2, wp=self.wp2)
        ServiceRequest.objects.filter(pk=sr.pk).update(status='in_progress')
        r = post_json(self.client_c, f'/api/v1/clients/requests/{sr.id}/complete/')
        self.assertEqual(r.status_code, 200, r.content)
        for wp in (self.wp, self.wp2):
            wp.refresh_from_db()
            self.assertEqual(wp.total_earnings, D('25000'))

    def test_worker_cannot_touch_someone_elses_assignment(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        w2 = Client()
        w2.force_login(self.worker2_user)
        self.assertEqual(post_json(w2, f'/api/v1/worker/my-assignments/{asg.id}/complete/').status_code, 404)

    def test_non_admin_cannot_assign(self):
        sr, _ = self.book()
        r = post_json(self.client_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        self.assertEqual(r.status_code, 403)


class PrivacyTests(FlowBase):
    def test_private_documents_owner_staff_or_signed_link_only(self):
        doc = WorkerDocument.objects.create(worker=self.wp, document_type='id', title='ID',
                                            file=SimpleUploadedFile('id.pdf', b'%PDF-1.4 x'))
        url = f'/media/{doc.file.name}'
        self.assertEqual(Client().get(url).status_code, 403)
        self.assertEqual(self.client_c.get(url).status_code, 403)
        for c in (self.worker_c, self.admin_c):
            r = c.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r['X-Accel-Redirect'], f'/protected-media/{doc.file.name}')
        # the app's link works without a login, a forged one does not
        r = self.worker_c.get('/api/v1/workers/documents/')
        file_url = next(d['file_url'] for d in r.json()['documents'] if d['id'] == doc.id) \
            if r.status_code == 200 and 'documents' in r.json() else None
        if file_url:
            path = file_url.split('testserver', 1)[1]
            self.assertEqual(Client().get(path).status_code, 200)
            self.assertEqual(Client().get(url + '?sig=forged').status_code, 403)

    def test_user_search_never_returns_emails(self):
        sr, _ = self.book()
        self.assign_and_accept(sr)  # the client may only find workers they work with
        r = self.client_c.get('/api/messages/search-users/', {'q': 'admin'})
        self.assertNotIn(b'admin@t.co', r.content)
        r = self.client_c.get('/api/messages/search-users/', {'q': 'Wor'})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('username', r.json()['users'][0])
        self.assertIn(b'clientone', self.admin_c.get('/api/messages/search-users/', {'q': 'clientone'}).content)

    def test_public_job_search_hides_address(self):
        self.book()
        r = Client().get('/api/search/jobs/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'Secret Street', r.content)
        self.assertIn(b'Secret Street', self.client_c.get('/api/v1/client/service-requests/').content)

    def test_review_requires_completed_work_together(self):
        r = post_json(self.other_client and self.client_c, '/api/v1/job-reviews/',
                      {'reviewee_id': self.worker2_user.id, 'overall_rating': 1, 'comment': 'fake'})
        self.assertEqual(r.status_code, 403)

    def test_api_docs_not_public(self):
        self.assertIn(Client().get('/api/docs/').status_code, (401, 403))

    def test_agent_finds_worker_by_exact_contact_only(self):
        WorkerProfile.objects.filter(pk=self.wp2.pk).update(agent=None)
        ag = Client()
        ag.force_login(self.agent_user)
        self.assertNotIn(b'worker2@t.co', ag.get('/agents/workers/search/', {'q': 'worker'}).content)
        self.assertIn(b'worker2@t.co', ag.get('/agents/workers/search/', {'q': 'worker2@t.co'}).content)


class NotificationTests(FlowBase):
    def test_unread_filter_and_push_token_follow_the_user(self):
        from worker_connect.notification_models import Notification, PushToken
        from worker_connect.notification_service import NotificationService
        NotificationService.create_notification(recipient=self.client_user, title='a', message='a',
                                                notification_type='system_alert')
        n = Notification.objects.filter(recipient=self.client_user).first()
        n.is_read = True
        n.save()
        NotificationService.create_notification(recipient=self.client_user, title='b', message='b',
                                                notification_type='system_alert')
        r = self.client_c.get('/api/notifications/', {'is_read': 'false'})
        self.assertEqual([x['title'] for x in r.json()], ['b'])

        token = 'ExponentPushToken[same-phone]'
        for c in (self.client_c, self.worker_c):
            r = post_json(c, '/api/notifications/push-token/register/', {'token': token, 'device_type': 'android'})
            self.assertEqual(r.status_code, 200, r.content)
        pt = PushToken.objects.get(token=token)
        self.assertEqual(pt.user, self.worker_user)
        self.assertTrue(pt.is_active)

        api_token = post_json(Client(), '/api/auth/login/', {'email': 'workerw', 'password': PW}).json()['token']
        post_json(Client(), '/api/auth/logout/', {'push_token': token}, HTTP_AUTHORIZATION=f'Token {api_token}')
        pt.refresh_from_db()
        self.assertFalse(pt.is_active)


class PagesRenderTests(FlowBase):
    def test_each_role_dashboard_loads(self):
        ag = Client()
        ag.force_login(self.agent_user)
        for c, url in [(self.client_c, '/clients/dashboard/'), (self.worker_c, '/workers/dashboard/'),
                       (self.admin_c, '/dashboard/'), (ag, '/agents/'), (Client(), '/'),
                       (Client(), '/accounts/login/'), (Client(), '/accounts/register/')]:
            r = c.get(url, follow=True)
            self.assertEqual(r.status_code, 200, url)


class EmailTests(FlowBase):
    def test_welcome_email_on_signup_from_app_and_website(self):
        from unittest import mock
        from django.core import mail
        from workers.tasks import send_welcome_email

        run_now = mock.patch.object(send_welcome_email, 'delay',
                                    side_effect=lambda uid, kind: send_welcome_email(uid, kind))
        with run_now, self.captureOnCommitCallbacks(execute=True):
            post_json(Client(), '/api/auth/register/', {
                'firstName': 'Asha', 'lastName': 'J', 'email': 'asha@t.co', 'phone': '0766000111',
                'password': PW, 'userType': 'client'})
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['asha@t.co'])
        html = msg.alternatives[0][0]
        self.assertIn('https://workersearch.co.tz/accounts/login/', html)
        self.assertNotIn('localhost', html)
        self.assertNotIn('portfolio', html.lower())

        # admins created by staff get no welcome mail
        with run_now, self.captureOnCommitCallbacks(execute=True):
            User.objects.create_user(email='ops@t.co', username='ops', password=PW,
                                     user_type='admin', is_staff=True)
        self.assertEqual(len(mail.outbox), 1)

    def test_job_reminder_reaches_client_and_accepted_workers(self):
        from datetime import timedelta
        from unittest import mock
        from jobs.tasks import send_job_reminders, send_job_reminder_email

        sr, _ = self.book()
        self.assign_and_accept(sr)
        tomorrow = timezone.now().date() + timedelta(days=1)
        ServiceRequest.objects.filter(pk=sr.pk).update(preferred_date=tomorrow, service_start_date=None)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'in_progress')  # accepting moves it on

        with mock.patch.object(send_job_reminder_email, 'delay') as queued:
            send_job_reminders()
        recipients = sorted(call.args[0] for call in queued.call_args_list)
        self.assertEqual(recipients, sorted([self.client_user.email, self.worker_user.email]))


class WorkerProfileTests(FlowBase):
    def test_adding_the_same_custom_skill_twice_is_not_an_error(self):
        for _ in range(2):
            r = self.worker_c.post('/workers/custom-skills/add/',
                                   {'name': 'House Painting', 'description': 'walls', 'years_of_experience': 2})
            self.assertEqual(r.status_code, 302)
        self.assertEqual(self.wp.custom_skills.filter(name='House Painting').count(), 1)


class AssignmentOptionTests(FlowBase):
    """The three ways a client gets a worker, on the app API and the website."""

    def setUp(self):
        super().setUp()
        # both workers in Dar; worker 2 is the closer one to the request below
        WorkerProfile.objects.filter(pk=self.wp.pk).update(latitude=-6.90, longitude=39.30, city='Dar')
        WorkerProfile.objects.filter(pk=self.wp2.pk).update(latitude=-6.80, longitude=39.28, city='Dar')
        self.unverified_user = User.objects.create_user(
            email='newbie@t.co', username='newbie', password=PW, user_type='worker', first_name='New')
        self.unverified = WorkerProfile.objects.create(user=self.unverified_user, verification_status='pending',
                                                       availability='available', is_public=True, city='Dar')
        self.unverified.categories.add(self.cat)

    def verify_payment(self, sr):
        sr.payment_screenshot = SimpleUploadedFile('p.png', PNG, 'image/png')
        sr.save()
        r = self.admin_c.post(f'/dashboard/service-requests/{sr.id}/verify-payment/')
        self.assertEqual(r.status_code, 302)
        sr.refresh_from_db()
        return sr

    def workers_on(self, sr):
        return set(sr.assignments.values_list('worker_id', flat=True))

    def web_booking(self, **extra):
        return self.client_c.post('/services/client/request-service/', {
            'category': self.cat.id, 'title': 'Fix sink', 'description': 'leaking', 'location': 'Mikocheni',
            'city': 'Dar', 'duration_type': 'daily', 'workers_needed': 1, 'urgency': 'normal',
            'preferred_date': str(timezone.now().date()), 'payment_method': 'yas', **extra})

    # -- 1. admin chooses --------------------------------------------------
    def test_admin_choice_waits_for_the_admin(self):
        sr, _ = self.book()
        self.assertEqual(sr.assignment_mode, 'admin_choice')
        sr = self.verify_payment(sr)
        self.assertEqual(self.workers_on(sr), set())
        r = post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        self.assertIn(r.status_code, (200, 201), r.content)
        self.assertEqual(self.workers_on(sr), {self.wp.id})

    # -- 2. client chooses -------------------------------------------------
    def test_browse_list_keeps_workers_without_location_and_hides_unverified(self):
        WorkerProfile.objects.filter(pk=self.wp.pk).update(latitude=None, longitude=None)
        r = self.client_c.get('/api/v1/client/browse-workers/',
                              {'category': self.cat.id, 'latitude': -6.79, 'longitude': 39.27})
        self.assertEqual(r.status_code, 200)
        ids = [w['id'] for w in r.json()['workers']]
        self.assertEqual(ids, [self.wp2.id, self.wp.id])  # located first, then the rest
        self.assertIsNotNone(r.json()['workers'][0]['distance_km'])
        self.assertIsNone(r.json()['workers'][1]['distance_km'])
        self.assertNotIn(self.unverified.id, ids)

    def test_client_choice_on_the_app(self):
        sr, _ = self.book(preferred_worker=self.wp2.id, assignment_mode='client_choice')
        self.assertEqual((sr.assignment_mode, sr.preferred_worker_id), ('client_choice', self.wp2.id))
        # the admin confirms the requested worker with one click
        sr = self.verify_payment(sr)
        r = self.admin_c.post(f'/dashboard/service-requests/{sr.id}/assign/', {'worker_id': self.wp2.id})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.workers_on(sr), {self.wp2.id})

    def test_client_cannot_pick_an_unverified_worker(self):
        total = float(self.cat.daily_rate + self.cat.service_fee)
        for url in ('/api/v1/client/service-requests/create/', f'/api/v1/clients/services/{self.cat.id}/request/'):
            ref = post_json(self.client_c, '/api/v1/client/process-payment/',
                            {'amount': total, 'payment_type': 'yas'}).json()['transaction_id']
            body = {'category': self.cat.id, 'title': 'x', 'description': 'x', 'location': 'x', 'city': 'Dar',
                    'workers_needed': 1, 'duration_type': 'daily', 'preferred_date': str(timezone.now().date()),
                    'preferred_time': '09:00:00', 'payment_transaction_id': ref, 'payment_method': 'yas',
                    'preferred_worker': self.unverified.id, 'assignment_mode': 'client_choice'}
            r = post_json(self.client_c, url, body)
            self.assertEqual(r.status_code, 400, f'{url}: {r.content}')
        r = self.web_booking(assignment_mode='client_choice', preferred_worker=self.unverified.id)
        self.assertFalse(ServiceRequest.objects.filter(preferred_worker=self.unverified).exists())

    def test_mode_follows_whether_a_worker_was_picked(self):
        sr, _ = self.book(preferred_worker=self.wp.id, assignment_mode='admin_choice')
        self.assertEqual(sr.assignment_mode, 'client_choice')
        sr, _ = self.book(assignment_mode='client_choice')
        self.assertEqual(sr.assignment_mode, 'admin_choice')

    def test_client_choice_on_the_website(self):
        r = self.web_booking(assignment_mode='client_choice', preferred_worker=self.wp.id)
        self.assertEqual(r.status_code, 302)
        sr = ServiceRequest.objects.filter(client=self.client_user).latest('id')
        self.assertEqual((sr.assignment_mode, sr.preferred_worker_id), ('client_choice', self.wp.id))

    # -- 3. nearest automatically ------------------------------------------
    def test_nearest_by_gps_after_payment_is_verified(self):
        sr, _ = self.book(assignment_mode='auto_nearest', latitude=-6.79, longitude=39.27)
        self.assertEqual(self.workers_on(sr), set())  # not before payment
        sr = self.verify_payment(sr)
        self.assertEqual(self.workers_on(sr), {self.wp2.id})  # the closer one
        self.assertEqual(sr.status, 'assigned')

    def test_nearest_falls_back_to_same_city_without_gps(self):
        WorkerProfile.objects.filter(pk__in=[self.wp.pk, self.wp2.pk]).update(latitude=None, longitude=None)
        WorkerProfile.objects.filter(pk=self.wp2.pk).update(city='Arusha')
        sr, _ = self.book(assignment_mode='auto_nearest')  # city Dar, no coordinates
        sr = self.verify_payment(sr)
        self.assertEqual(self.workers_on(sr), {self.wp.id})
        self.assertEqual(sr.assignment_mode, 'auto_nearest')

    def test_nearest_never_picks_busy_or_unverified_and_falls_back_to_admin(self):
        WorkerProfile.objects.filter(pk__in=[self.wp.pk, self.wp2.pk]).update(availability='busy')
        sr, _ = self.book(assignment_mode='auto_nearest', latitude=-6.79, longitude=39.27)
        sr = self.verify_payment(sr)
        self.assertEqual(self.workers_on(sr), set())
        self.assertEqual(sr.assignment_mode, 'admin_choice')

    def test_nearest_fills_every_slot(self):
        sr, _ = self.book(workers=2, assignment_mode='auto_nearest', latitude=-6.79, longitude=39.27)
        sr = self.verify_payment(sr)
        self.assertEqual(self.workers_on(sr), {self.wp.id, self.wp2.id})
        self.assertEqual(sr.status, 'assigned')

    def test_nearest_on_the_website(self):
        r = self.web_booking(assignment_mode='auto_nearest', latitude='-6.79', longitude='39.27')
        self.assertEqual(r.status_code, 302)
        sr = ServiceRequest.objects.filter(client=self.client_user).latest('id')
        self.assertEqual(sr.assignment_mode, 'auto_nearest')
        sr = self.verify_payment(sr)
        self.assertEqual(self.workers_on(sr), {self.wp2.id})

    # -- both booking pages offer all three ---------------------------------
    def test_category_booking_link_opens_the_main_page_preselected(self):
        r = self.client_c.get(f'/clients/services/{self.cat.id}/request/')
        self.assertEqual(r.status_code, 302)
        self.assertIn(f'request-service/?category={self.cat.id}', r['Location'])
        page = self.client_c.get(r['Location']).content.decode()
        self.assertIn(f'value="{self.cat.id}" selected', page)
        for mode in ('admin_choice', 'client_choice', 'auto_nearest'):
            self.assertIn(f'value="{mode}"', page)


class WorkerLocationTests(FlowBase):
    def test_dashboard_prompt_and_one_tap_save(self):
        self.assertIn('Save my location', self.worker_c.get('/workers/dashboard/').content.decode())
        self.assertEqual(self.worker_c.post('/workers/location/', {'latitude': 'x', 'longitude': '1'}).status_code, 400)
        self.assertEqual(self.worker_c.post('/workers/location/', {'latitude': '200', 'longitude': '1'}).status_code, 400)
        self.assertEqual(self.client_c.post('/workers/location/', {'latitude': '-6.8', 'longitude': '39.2'}).status_code, 403)
        r = self.worker_c.post('/workers/location/', {'latitude': '-6.8', 'longitude': '39.2'})
        self.assertEqual(r.status_code, 200)
        self.wp.refresh_from_db()
        self.assertEqual((self.wp.latitude, self.wp.longitude), (-6.8, 39.2))
        self.assertNotIn('Save my location', self.worker_c.get('/workers/dashboard/').content.decode())

    def test_app_can_save_location(self):
        r = self.worker_c.patch('/api/workers/profile/update/', json.dumps({'latitude': -6.81, 'longitude': 39.29}),
                                content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.latitude, -6.81)

    def test_reminder_command_previews_unless_told_to_send(self):
        from io import StringIO
        from django.core.management import call_command
        from worker_connect.notification_models import Notification
        out = StringIO()
        call_command('notify_workers_location', stdout=out)
        self.assertIn('Preview only', out.getvalue())
        self.assertEqual(Notification.objects.filter(title__startswith='Get jobs near you').count(), 0)
        call_command('notify_workers_location', '--send', stdout=StringIO())
        self.assertEqual(Notification.objects.filter(title__startswith='Get jobs near you').count(), 2)


class PublicPagesTests(FlowBase):
    def test_robots_and_staff_only_detailed_health(self):
        r = Client().get('/robots.txt')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Disallow: /dashboard/', r.content.decode())
        self.assertIn(Client().get('/api/health/detailed/').status_code, (401, 403))
        self.assertEqual(Client().get('/api/health/').status_code, 200)


class CityMatchingTests(FlowBase):
    def test_city_spellings_and_neighbourhoods_match(self):
        from workers.cities import city_key
        for typed in ['Zanzibar', 'ZANZIBAR', 'zanzibar', 'Zanzibra', 'STONETOWN', 'Stone Town',
                      'Fuoni', 'mbweni', 'Fuoni, Zanzibar', ' zanzibar  ']:
            self.assertEqual(city_key(typed), 'zanzibar', typed)
        for typed in ['Dar es Salaam', 'Dar es salaam', 'DSM', 'Dar', 'Kinondoni']:
            self.assertEqual(city_key(typed), 'dar es salaam', typed)
        self.assertEqual(city_key('Dodoma'), 'dodoma')
        self.assertEqual(city_key(''), '')
        self.assertNotEqual(city_key('Arusha'), city_key('Zanzibar'))

    def test_nearest_matches_a_worker_who_typed_a_neighbourhood(self):
        WorkerProfile.objects.filter(pk=self.wp.pk).update(latitude=None, longitude=None, city='STONETOWN')
        WorkerProfile.objects.filter(pk=self.wp2.pk).update(latitude=None, longitude=None, city='Arusha')
        sr, _ = self.book(assignment_mode='auto_nearest', city='zanzibar')
        sr.payment_screenshot = SimpleUploadedFile('p.png', PNG, 'image/png')
        sr.save()
        self.admin_c.post(f'/dashboard/service-requests/{sr.id}/verify-payment/')
        self.assertEqual(set(sr.assignments.values_list('worker_id', flat=True)), {self.wp.id})


class VerificationQueueTests(FlowBase):
    """One page to review a worker and their documents; filters that filter."""

    def setUp(self):
        super().setUp()
        from worker_connect.notification_models import Notification
        self.Notification = Notification
        self.pending_user = User.objects.create_user(
            email='pend@t.co', username='pendy', password=PW, user_type='worker',
            first_name='Pendo', last_name='Ali', phone_number='0777123456')
        self.pending = WorkerProfile.objects.create(user=self.pending_user, verification_status='pending', city='Zanzibar')
        self.id_doc = WorkerDocument.objects.create(worker=self.pending, document_type='id', title='ID',
                                                    file=SimpleUploadedFile('id.png', PNG))
        self.rejected_user = User.objects.create_user(email='rej@t.co', username='rejy', password=PW,
                                                      user_type='worker', first_name='Rajab')
        WorkerProfile.objects.create(user=self.rejected_user, verification_status='rejected')

    def names(self, **params):
        r = self.admin_c.get('/dashboard/workers/verification/', params)
        self.assertEqual(r.status_code, 200)
        return {w.user.first_name for w in r.context['page']}

    def test_status_filters_and_search(self):
        self.assertEqual(self.names(status='pending'), {'Pendo'})
        self.assertEqual(self.names(), {'Pendo'})  # pending is the default queue
        self.assertEqual(self.names(status='rejected'), {'Rajab'})
        self.assertEqual(self.names(status='verified'), {'Wor', 'Two'})
        self.assertEqual(self.names(status='all'), {'Pendo', 'Rajab', 'Wor', 'Two'})
        self.assertEqual(self.names(status='all', q='0777123'), {'Pendo'})
        self.assertEqual(self.names(status='all', q='zanzibar'), {'Pendo'})
        self.assertEqual(self.names(status='all', docs='waiting'), {'Pendo'})
        self.assertEqual(self.names(status='all', docs='none'), {'Rajab', 'Wor', 'Two'})

    def test_non_staff_cannot_open_the_queue(self):
        self.assertNotEqual(self.client_c.get('/dashboard/workers/verification/').status_code, 200)
        self.assertNotEqual(self.client_c.get(f'/dashboard/workers/verify/{self.pending.id}/').status_code, 200)

    def test_review_page_shows_profile_and_documents(self):
        page = self.admin_c.get(f'/dashboard/workers/verify/{self.pending.id}/').content.decode()
        self.assertIn('Pendo Ali', page)
        self.assertIn('0777123456', page)
        self.assertIn(self.id_doc.file.url, page)
        self.assertIn('Approve ID', page)

    def test_approve_id_and_verify_in_one_click_notifies_the_worker(self):
        r = self.admin_c.post(f'/dashboard/workers/verify/{self.pending.id}/', {'action': 'approve_id_and_verify'})
        self.assertEqual(r.status_code, 302)
        self.pending.refresh_from_db()
        self.id_doc.refresh_from_db()
        self.assertEqual((self.pending.verification_status, self.id_doc.verification_status), ('verified', 'approved'))
        self.assertTrue(self.Notification.objects.filter(recipient=self.pending_user, title__startswith='You are verified').exists())

    def test_cannot_verify_without_an_approved_id(self):
        self.admin_c.post(f'/dashboard/workers/verify/{self.pending.id}/', {'action': 'verify'})
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.verification_status, 'pending')

    def test_document_decisions_on_the_same_page(self):
        url = f'/dashboard/workers/verify/{self.pending.id}/'
        # a rejection needs a reason, and the worker hears it
        self.admin_c.post(url, {'action': 'reject_doc', 'doc_id': self.id_doc.id})
        self.id_doc.refresh_from_db()
        self.assertEqual(self.id_doc.verification_status, 'pending')
        r = self.admin_c.post(url, {'action': 'reject_doc', 'doc_id': self.id_doc.id, 'reason': 'photo is blurry'})
        self.assertRedirects(r, url, fetch_redirect_response=False)
        self.id_doc.refresh_from_db()
        self.assertEqual((self.id_doc.verification_status, self.id_doc.rejection_reason), ('rejected', 'photo is blurry'))
        n = self.Notification.objects.get(recipient=self.pending_user, title='Document needs attention')
        self.assertIn('photo is blurry', n.message)
        self.admin_c.post(url, {'action': 'approve_doc', 'doc_id': self.id_doc.id})
        self.id_doc.refresh_from_db()
        self.assertEqual(self.id_doc.verification_status, 'approved')
        # another worker's document cannot be decided from this page
        other = WorkerDocument.objects.create(worker=self.wp, document_type='cv', title='CV',
                                              file=SimpleUploadedFile('cv.pdf', b'%PDF-1.4'))
        self.assertEqual(self.admin_c.post(url, {'action': 'approve_doc', 'doc_id': other.id}).status_code, 404)

    def test_reject_worker_needs_reason_and_goes_to_next(self):
        url = f'/dashboard/workers/verify/{self.pending.id}/'
        self.admin_c.post(url, {'action': 'reject'})
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.verification_status, 'pending')
        nxt_user = User.objects.create_user(email='nx@t.co', username='nexty', password=PW, user_type='worker', first_name='Next')
        nxt = WorkerProfile.objects.create(user=nxt_user, verification_status='pending')
        r = self.admin_c.post(url, {'action': 'reject', 'reason': 'fake ID', 'then': 'next'})
        self.assertRedirects(r, f'/dashboard/workers/verify/{nxt.id}/', fetch_redirect_response=False)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.verification_status, 'rejected')
        self.assertIn('fake ID', self.Notification.objects.get(recipient=self.pending_user, title='Verification not approved').message)

    def test_old_document_pages_lead_to_the_review_page(self):
        self.assertRedirects(self.admin_c.get('/dashboard/documents/'),
                             '/dashboard/workers/verification/?status=all&docs=waiting', fetch_redirect_response=False)
        r = self.admin_c.post(f'/dashboard/documents/verify/{self.id_doc.id}/', {'action': 'approve'})
        self.assertRedirects(r, f'/dashboard/workers/verify/{self.pending.id}/', fetch_redirect_response=False)
        self.id_doc.refresh_from_db()
        self.assertEqual(self.id_doc.verification_status, 'approved')


class AdminSearchAndFilterTests(FlowBase):
    def test_header_search_finds_people_and_bookings(self):
        sr, _ = self.book()
        for q, expected in [('0744555666', 'Wor Ker'), ('Cli One', 'Cli'), (f'#{sr.id}', 'Leaky tap'), ('clientone', 'Cli')]:
            r = self.admin_c.get('/dashboard/search/', {'q': q})
            self.assertEqual(r.status_code, 200)
            self.assertIn(expected, r.content.decode(), q)
        self.assertNotEqual(self.client_c.get('/dashboard/search/', {'q': 'a'}).status_code, 200)
        self.assertIn('name="q"', self.admin_c.get('/dashboard/').content.decode())

    def test_payment_filter_tells_no_proof_from_waiting(self):
        no_proof, _ = self.book()
        with_proof, _ = self.book()
        with_proof.payment_screenshot = SimpleUploadedFile('p.png', PNG, 'image/png')
        with_proof.save()

        def ids(payment):
            r = self.admin_c.get('/dashboard/service-requests/', {'payment': payment})
            return {req.id for req in r.context['page_obj']}
        self.assertEqual(ids('none'), {no_proof.id})
        self.assertEqual(ids('pending'), {with_proof.id})
        self.admin_c.post(f'/dashboard/service-requests/{with_proof.id}/verify-payment/')
        self.assertEqual(ids('verified'), {with_proof.id})

    def test_users_filter_agents_and_search_usernames(self):
        r = self.admin_c.get('/dashboard/users/', {'type': 'agent'})
        emails = {u['user'].email for u in r.context['users_page']}
        self.assertEqual(emails, {'agent@t.co'})
        r = self.admin_c.get('/dashboard/users/', {'search': 'workertwo'})
        self.assertEqual({u['user'].email for u in r.context['users_page']}, {'worker2@t.co'})


class NotificationLinkTests(FlowBase):
    def test_bells_show_live_counts_and_notifications_open_their_page(self):
        from worker_connect.notification_models import Notification
        from worker_connect.notification_service import NotificationService
        sr, _ = self.book()
        for c in (self.admin_c, self.client_c):
            page = c.get('/dashboard/' if c is self.admin_c else '/clients/dashboard/', follow=True).content.decode()
            self.assertIn('header-notification-badge', page)
            self.assertNotIn('<span class="notification-badge">3</span>', page)
        NotificationService.create_notification(recipient=self.client_user, title='Worker assigned', message='x',
                                                notification_type='job_assigned', extra_data={'service_request_id': sr.id})
        n = Notification.objects.filter(recipient=self.client_user, title='Worker assigned').latest('id')
        self.assertEqual(self.client_c.get('/notifications/unread-count/').json()['count'],
                         Notification.objects.filter(recipient=self.client_user, is_read=False).count())
        r = self.client_c.get(f'/notifications/{n.id}/open/')
        self.assertRedirects(r, f'/services/client/request/{sr.id}/', fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.is_read)
        # someone else's notification cannot be opened
        self.assertEqual(self.worker_c.get(f'/notifications/{n.id}/open/').status_code, 404)
        self.assertIn(f'/notifications/{n.id}/open/', self.client_c.get('/notifications/').content.decode())

    def test_client_header_search_filters_services(self):
        Category.objects.create(name='Electrician', daily_rate=D('30000'), service_fee=D('5000'))
        r = self.client_c.get('/clients/services/', {'q': 'plumb'})
        self.assertEqual([s['name'] for s in r.context['services']], ['Plumber'])


class ClientPagesTests(FlowBase):
    def test_home_page_shows_real_numbers_and_right_buttons(self):
        r = Client().get('/')
        page = r.content.decode()
        for fake in ('500+', '300+', '50+', '98%'):
            self.assertNotIn(f'>{fake}<', page)
        self.assertEqual(r.context['verified_workers'], 2)
        self.assertEqual(r.context['registered_workers'], 2)
        self.assertIn(f'<div class="hero-stat-num">{r.context["verified_workers"]}</div>', page)
        self.assertIn('href="/accounts/register/client/" class="btn-hero-outline"', page)  # Request Service
        self.assertIn('href="/services/client/request-service/" class="btn-hero-outline"',
                      self.client_c.get('/').content.decode())  # signed-in client books directly

    def test_menu_links_have_no_underline_or_border(self):
        page = Client().get('/').content.decode()
        self.assertIn('#navbarNav .btn-nav-signup { text-decoration: none !important; }', page)
        self.assertIn('#navbarNav .btn-nav-signup { border: none !important; }', page)

    def test_booking_page_prices_per_request_like_the_server(self):
        page = self.client_c.get('/services/client/request-service/').content.decode()
        self.assertIn('data-service-fee="5000', page)
        self.assertNotIn('durationDays * dailyRate', page)
        self.assertNotIn('Workers × Days', page)

    def test_cancel_needs_only_a_reason_from_the_list(self):
        sr, _ = self.book()
        url = f'/services/client/request/{sr.id}/cancel/'
        page = self.client_c.get(url).content.decode()
        self.assertIn('Cancel this booking?', page)
        self.client_c.post(url, {'cancellation_reason_type': 'made_up'})
        sr.refresh_from_db()
        self.assertNotEqual(sr.status, 'cancelled')
        r = self.client_c.post(url, {'cancellation_reason_type': 'no_longer_needed'})
        self.assertEqual(r.status_code, 302)
        sr.refresh_from_db()
        self.assertEqual(sr.status, 'cancelled')
        self.assertIn('No longer needed', sr.cancellation_reason)

    def test_booking_detail_shows_progress_and_no_leaked_comment(self):
        sr, _ = self.book()
        page = self.client_c.get(f'/services/client/request/{sr.id}/').content.decode()
        self.assertNotIn('{#', page)
        self.assertIn('Payment verified', page)
        self.assertIn('TSh 30,000', page)


class DashboardTests(FlowBase):
    def test_admin_dashboard_counts_real_work_and_has_no_made_up_numbers(self):
        sr, _ = self.book()
        sr.payment_screenshot = SimpleUploadedFile('p.png', PNG, 'image/png')
        sr.save()
        r = self.admin_c.get('/dashboard/')
        self.assertEqual(r.status_code, 200)
        page = r.content.decode()
        for fake in ('+5.8%', '+6.0%', '-2.1%', '15 Oct', '>Send<'):
            self.assertNotIn(fake, page)
        counts = {a['label']: a['count'] for a in r.context['attention']}
        self.assertEqual(counts['Payment proofs to check'], 1)
        self.assertEqual(counts['Agents to approve'], 0)
        self.assertEqual(len(r.context['days']), 14)

    def test_one_client_home_and_the_old_one_redirects(self):
        sr, _ = self.book()
        page = self.client_c.get('/clients/dashboard/').content.decode()
        self.assertIn('Leaky tap', page)
        self.assertIn('upload your payment proof', page)
        self.assertRedirects(self.client_c.get('/services/client/dashboard/'), '/clients/dashboard/',
                             fetch_redirect_response=False)
        self.assertNotIn('SR Dashboard', page)

    def test_worker_home_shows_jobs_waiting_and_what_is_missing(self):
        sr, _ = self.book()
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        page = self.worker_c.get('/workers/dashboard/').content.decode()
        self.assertIn('Leaky tap', page)
        self.assertIn('Upload your ID', page)
        self.assertRedirects(self.worker_c.get('/services/worker/dashboard/'), '/workers/dashboard/',
                             fetch_redirect_response=False)
        self.assertIn('header-notification-badge', page)

    def test_my_bookings_keeps_search_when_switching_tabs(self):
        self.book()
        r = self.client_c.get('/services/client/my-requests/', {'search': 'Leaky', 'status': 'pending'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('href="?status=completed&amp;search=Leaky"', r.content.decode())

    def test_new_pages_speak_swahili(self):
        self.client_c.cookies['django_language'] = 'sw'
        page = self.client_c.get('/services/client/request-service/').content.decode()
        self.assertIn('Unahitaji nini?', page)
        self.assertIn('Lipa na weka miadi', page)


class WorkerJobPageTests(FlowBase):
    def test_worker_sees_their_pay_and_client_phone_only_after_accepting(self):
        sr, _ = self.book()
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        asg = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp)
        url = f'/services/worker/assignment/{asg.id}/'
        page = self.worker_c.get(url).content.decode()
        self.assertIn('TSh 25,000', page)          # what the worker earns
        self.assertNotIn('TSh 30,000', page)       # not the client's total with the fee
        self.assertNotIn(self.client_user.phone_number, page)
        self.assertIn('Accept job', page)
        post_json(self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/respond/', {'accepted': True})
        page = self.worker_c.get(url).content.decode()
        self.assertIn(f'tel:{self.client_user.phone_number}', page)
        self.assertIn('Clock in', page)
        self.assertIn('google.com/maps', page)

    def test_profile_edit_has_category_search(self):
        page = self.worker_c.get('/workers/profile/edit/').content.decode()
        self.assertIn('id="categorySearch"', page)
        self.assertNotIn('experience, and rates', page)

    def test_admin_booking_page_shows_price_breakdown(self):
        sr, _ = self.book()
        page = self.admin_c.get(f'/dashboard/service-requests/{sr.id}/').content.decode()
        self.assertIn('TSh 30,000', page)
        self.assertNotIn('None hours', page)


class TemplateHygieneTests(TestCase):
    def test_no_template_has_a_multiline_hash_comment(self):
        # {# #} only works on one line; a multi-line one is printed on the page
        import re
        from pathlib import Path
        from django.conf import settings
        bad = []
        for path in Path(settings.BASE_DIR, 'templates').rglob('*.html'):
            text = path.read_text(encoding='utf-8', errors='ignore')
            for m in re.finditer(r'\{#(?:(?!#\}).)*?\n', text, re.S):
                bad.append(f'{path.name}:{text[:m.start()].count(chr(10)) + 1}')
        self.assertEqual(bad, [])

    def test_emails_have_real_contact_details(self):
        from django.template.loader import render_to_string
        html = render_to_string('emails/generic_notification.html', {'title': 't', 'message': 'm'})
        self.assertNotIn('Business Street', html)
        self.assertNotIn('href="#"', html)
        self.assertIn('sales@easyfix.co.tz', html)


class AdminMenuTests(FlowBase):
    def test_one_menu_entry_for_workers_and_documents(self):
        page = self.admin_c.get('/dashboard/').content.decode()
        self.assertNotIn('Document Reviews', page)
        self.assertNotIn('Worker Verifications', page)
        self.assertIn('>Verifications<', page)

    def test_sidebar_shows_who_is_signed_in(self):
        for c, url in [(self.admin_c, '/dashboard/'), (self.client_c, '/clients/dashboard/'), (self.worker_c, '/workers/dashboard/')]:
            page = c.get(url).content.decode()
            self.assertIn('ui-side-user', page, url)
            self.assertIn('ui-hero', page, url)

    def test_tables_have_a_serial_number_in_the_header_row(self):
        import re
        for url in ['/dashboard/workers/verification/?status=all', '/dashboard/users/', '/dashboard/service-requests/']:
            page = self.admin_c.get(url).content.decode()
            head = re.search(r'<thead[^>]*>\s*<tr[^>]*>\s*<th class="ui-sn">SN</th>', page)
            self.assertIsNotNone(head, url)


class MissingFileTests(FlowBase):
    def test_review_page_says_when_a_document_file_is_missing(self):
        doc = WorkerDocument.objects.create(worker=self.wp, document_type='id', title='ID',
                                            file='worker_documents/lost-in-move.png', verification_status='approved')
        WorkerProfile.objects.filter(pk=self.wp.pk).update(profile_image='worker_profiles/lost.png')
        self.wp.refresh_from_db()
        self.assertTrue(doc.file_missing)
        self.assertIsNone(self.wp.photo_url)
        page = self.admin_c.get(f'/dashboard/workers/verify/{self.wp.id}/').content.decode()
        self.assertIn('File missing on the server', page)
        self.assertIn('Ask to upload again', page)
        self.assertNotIn('worker_profiles/lost.png', page)  # no broken photo
        # asking for a new upload tells the worker
        from worker_connect.notification_models import Notification
        self.admin_c.post(f'/dashboard/workers/verify/{self.wp.id}/', {
            'action': 'reject_doc', 'doc_id': doc.id,
            'reason': 'Your file could not be found on our system. Please upload it again'})
        self.assertTrue(Notification.objects.filter(recipient=self.worker_user, title='Document needs attention').exists())

    def test_all_signed_in_layouts_load_the_shared_design(self):
        for c, url in [(self.admin_c, '/dashboard/'), (self.client_c, '/clients/dashboard/'), (self.worker_c, '/workers/dashboard/')]:
            # versioned so browsers never keep an old copy (static files are cached 30 days)
            self.assertRegex(c.get(url).content.decode(), r'css/ui\.css\?v=[0-9a-f]{8}', url)


class ChatTests(FlowBase):
    """Workers and clients chat only once the worker has accepted the job; everyone can reach support."""

    def send(self, c, to, text='hello'):
        return c.post(f'/jobs/conversation/{to.id}/', {'message': text})

    def test_no_chat_before_the_worker_accepts(self):
        sr, _ = self.book()
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        # assigned but not accepted yet: no chat either way, web or app
        self.send(self.client_c, self.worker_user)
        self.send(self.worker_c, self.client_user)
        self.assertFalse(Message.objects.filter(sender__in=[self.client_user, self.worker_user]).exists())
        r = self.client_c.get(f'/jobs/conversation/{self.worker_user.id}/')
        self.assertRedirects(r, '/jobs/inbox/', fetch_redirect_response=False)
        r = post_json(self.worker_c, '/api/messages/send/', {'recipient_id': self.client_user.id, 'message': 'hi'})
        self.assertEqual(r.status_code, 403)
        self.assertNotContains(self.client_c.get('/jobs/inbox/'), 'Wor Ker')

    def test_chat_opens_after_accept_both_ways(self):
        sr, _ = self.book()
        self.assign_and_accept(sr)
        inbox = self.client_c.get('/jobs/inbox/')
        self.assertContains(inbox, 'Wor Ker')
        self.assertContains(inbox, 'Leaky tap')
        self.send(self.client_c, self.worker_user, 'When can you come?')
        r = self.worker_c.get(f'/jobs/conversation/{self.client_user.id}/')
        self.assertContains(r, 'When can you come?')
        self.assertContains(r, 'name="message"')
        r = post_json(self.worker_c, '/api/messages/send/', {'recipient_id': self.client_user.id, 'message': 'At 9'})
        self.assertEqual(r.status_code, 200, r.content)
        convs = self.client_c.get('/api/messages/conversations/').json()['conversations']
        row = next(c for c in convs if c['id'] == self.worker_user.id)
        self.assertEqual(row['last_message'], 'At 9')
        self.assertEqual(row['unread_count'], 1)
        self.assertTrue(row['can_send'])

    def test_chat_closes_when_the_job_is_cancelled_but_history_stays(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        self.send(self.client_c, self.worker_user, 'first')
        ServiceRequestAssignment.objects.filter(pk=asg.pk).update(status='cancelled')
        r = self.client_c.get(f'/jobs/conversation/{self.worker_user.id}/')
        self.assertContains(r, 'first')
        self.assertContains(r, 'This chat is closed')
        self.assertNotContains(r, 'name="message"')
        self.send(self.client_c, self.worker_user, 'second')
        self.assertFalse(Message.objects.filter(message='second').exists())

    def test_other_people_stay_out(self):
        sr, _ = self.book()
        self.assign_and_accept(sr)
        other = Client(); other.force_login(self.other_client)
        w2 = Client(); w2.force_login(self.worker2_user)
        for c, to in ((other, self.worker_user), (w2, self.client_user), (self.worker_c, self.worker2_user),
                      (self.client_c, self.other_client)):
            self.assertEqual(post_json(c, '/api/messages/send/', {'recipient_id': to.id, 'message': 'x'}).status_code, 403)
            self.send(c, to, 'x')
        self.assertFalse(Message.objects.filter(message='x').exists())

    def test_everyone_can_reach_support_and_admin_can_reach_everyone(self):
        inbox = self.worker_c.get('/jobs/inbox/')
        self.assertContains(inbox, 'Worker Connect support')
        self.send(self.worker_c, self.admin, 'need help')
        self.send(self.admin_c, self.other_client, 'hello from admin')
        self.assertTrue(Message.objects.filter(message='need help', recipient=self.admin).exists())
        self.assertTrue(Message.objects.filter(message='hello from admin').exists())
        r = self.admin_c.get(f'/jobs/conversation/{self.worker_user.id}/')
        self.assertContains(r, 'need help')
        self.assertEqual(Message.objects.get(message='need help').is_read, True)
        self.assertContains(self.admin_c.get('/jobs/inbox/'), 'Wor Ker')

    def test_direct_booking_accept_opens_chat(self):
        from jobs.models import DirectHireRequest
        b = DirectHireRequest.objects.create(client=self.client_user, worker=self.wp2, title='Paint wall',
                                             description='x', location='Dar', duration_value=1,
                                             start_datetime=timezone.now(), offered_rate=D('1000'),
                                             total_amount=D('1000'))
        self.assertEqual(post_json(self.client_c, '/api/messages/send/',
                                   {'recipient_id': self.worker2_user.id, 'message': 'y'}).status_code, 403)
        DirectHireRequest.objects.filter(pk=b.pk).update(status='accepted')
        self.assertEqual(post_json(self.client_c, '/api/messages/send/',
                                   {'recipient_id': self.worker2_user.id, 'message': 'y'}).status_code, 200)

    def test_accepting_on_the_website_opens_chat_and_shows_chat_buttons(self):
        sr, _ = self.book()
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        asg = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp)
        page = self.worker_c.get(f'/services/worker/assignment/{asg.id}/').content.decode()
        self.assertNotIn('Chat with client', page)
        self.worker_c.post(f'/services/worker/assignment/{asg.id}/respond/', {'action': 'accept'})
        self.assertContains(self.worker_c.get(f'/services/worker/assignment/{asg.id}/'),
                            f'/jobs/conversation/{self.client_user.id}/')
        self.assertContains(self.client_c.get(f'/services/client/request/{sr.id}/'),
                            f'/jobs/conversation/{self.worker_user.id}/')
        self.send(self.worker_c, self.client_user, 'from the website')
        self.assertTrue(Message.objects.filter(message='from the website').exists())

    def test_one_alert_per_unread_batch_and_it_opens_the_chat(self):
        from worker_connect.notification_models import Notification
        before = Notification.objects.filter(recipient=self.admin).count()
        for t in ('a', 'b', 'c'):
            self.send(self.worker_c, self.admin, t)
        notes = Notification.objects.filter(recipient=self.admin).order_by('-id')
        self.assertEqual(notes.count() - before, 1)
        self.assertEqual(notes.first().target_url, f'/jobs/conversation/{self.worker_user.id}/')
        self.admin_c.get(f'/jobs/conversation/{self.worker_user.id}/')  # reads them
        self.send(self.worker_c, self.admin, 'd')  # still chatting: no new alert
        self.assertEqual(Notification.objects.filter(recipient=self.admin).count() - before, 1)
        from datetime import timedelta
        Message.objects.filter(sender=self.worker_user).update(created_at=timezone.now() - timedelta(minutes=30))
        self.admin_c.get(f'/jobs/conversation/{self.worker_user.id}/')
        self.send(self.worker_c, self.admin, 'e')  # later, after reading: alert again
        self.assertEqual(Notification.objects.filter(recipient=self.admin).count() - before, 2)

    def test_two_messages_at_once_still_alert_once(self):
        from worker_connect.notification_models import Notification
        from jobs.chat_access import notify_new_message
        m1 = Message.objects.create(sender=self.worker_user, recipient=self.admin, message='1')
        m2 = Message.objects.create(sender=self.worker_user, recipient=self.admin, message='2')
        notify_new_message(m2); notify_new_message(m1)  # both saved before either alert ran
        self.assertEqual(Notification.objects.filter(recipient=self.admin, notification_type='message_received').count(), 1)

    def test_app_never_hands_out_strangers_details(self):
        r = self.client_c.get(f'/api/messages/{self.worker2_user.id}/')
        self.assertEqual(r.status_code, 404)
        self.assertNotIn(b'worker2@t.co', r.content)
        self.assertNotIn(b'Two', r.content)
        r = self.client_c.get(f'/api/messages/{self.admin.id}/')  # support: allowed, but no e-mail
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'admin@t.co', r.content)
        self.assertNotIn(b'boss', r.content)
        self.assertNotIn(b'admin@t.co', self.client_c.get('/api/messages/conversations/').content)

    def test_deactivated_person_shows_a_closed_chat(self):
        Message.objects.create(sender=self.admin, recipient=self.worker_user, message='old')
        self.worker_user.is_active = False; self.worker_user.save()
        r = self.admin_c.get(f'/jobs/conversation/{self.worker_user.id}/')
        self.assertContains(r, 'old')
        self.assertContains(r, 'This chat is closed')
        convs = self.admin_c.get('/api/messages/conversations/').json()['conversations']
        self.assertFalse(next(c for c in convs if c['id'] == self.worker_user.id)['can_send'])

    def test_admin_without_staff_flag_can_search_everyone(self):
        ops = User.objects.create_user(email='ops2@t.co', username='ops2', password=PW, user_type='admin')
        c = Client(); c.force_login(ops)
        self.assertIn(b'clientone', c.get('/api/messages/search-users/', {'q': 'clientone'}).content)

    def test_agent_messages_page_uses_the_agent_layout(self):
        ag = Client(); ag.force_login(self.agent_user)
        r = ag.get('/jobs/inbox/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'agent-sidebar')
        self.assertContains(r, 'Worker Connect support')

    def test_chat_socket_groups_are_per_pair(self):
        from worker_connect.websocket_consumers import chat_group_name
        self.assertEqual(chat_group_name(5, 9), chat_group_name(9, 5))
        self.assertNotEqual(chat_group_name(5, 9), chat_group_name(7, 9))

    def test_phone_numbers_only_after_accept_in_the_app(self):
        """Calling uses these numbers, so they follow the same rule as chat."""
        client_phone, worker_phone = b'711222333', b'744555666'
        sr, _ = self.book()
        post_json(self.admin_c, f'/api/v1/admin/service-requests/{sr.id}/assign/', {'worker_id': self.wp.id})
        asg = ServiceRequestAssignment.objects.get(service_request=sr, worker=self.wp)
        worker_urls = ['/api/v1/worker/my-assignments/', '/api/v1/worker/my-assignments/pending/',
                       f'/api/v1/worker/my-assignments/{asg.id}/', '/api/v1/workers/assigned-jobs/',
                       '/api/v1/worker/service-requests/', f'/api/v1/worker/service-requests/{sr.id}/detail/']
        client_urls = ['/api/v1/client/service-requests/', f'/api/v1/client/service-requests/{sr.id}/']
        for u in worker_urls:
            r = self.worker_c.get(u)
            self.assertNotIn(client_phone, r.content, f'before accept, worker sees client phone at {u}')
            self.assertNotIn(b'Client.One@t.co'.lower(), r.content.lower(), u)
        for u in client_urls:
            self.assertNotIn(worker_phone, self.client_c.get(u).content, f'before accept, client sees worker phone at {u}')
        post_json(self.worker_c, f'/api/v1/worker/my-assignments/{asg.id}/respond/', {'accepted': True})
        self.assertIn(client_phone, self.worker_c.get(f'/api/v1/worker/my-assignments/{asg.id}/').content)
        self.assertIn(worker_phone, self.client_c.get(f'/api/v1/client/service-requests/{sr.id}/').content)

    def test_call_button_only_after_accept_web_and_app(self):
        sr, _ = self.book()
        asg = self.assign_and_accept(sr)
        # website: Call button with the other person's number, both ways
        self.assertContains(self.client_c.get(f'/jobs/conversation/{self.worker_user.id}/'), 'href="tel:0744555666"')
        self.assertContains(self.worker_c.get(f'/jobs/conversation/{self.client_user.id}/'), 'href="tel:+255711222333"')
        # app: the number comes with the chat and the chat list
        r = self.client_c.get(f'/api/messages/{self.worker_user.id}/').json()
        self.assertEqual(r['other_user']['phone_number'], '0744555666')
        convs = self.worker_c.get('/api/messages/conversations/').json()['conversations']
        self.assertEqual(next(c for c in convs if c['id'] == self.client_user.id)['phone_number'], '+255711222333')
        # support is reached by chat, not by phone
        self.admin.phone_number = '0700000000'; self.admin.save()
        self.assertNotContains(self.worker_c.get(f'/jobs/conversation/{self.admin.id}/'), 'tel:0700000000')
        # job cancelled: no more calling (the old chat stays readable)
        self.send(self.client_c, self.worker_user, 'see you')
        ServiceRequestAssignment.objects.filter(pk=asg.pk).update(status='cancelled')
        self.assertNotContains(self.client_c.get(f'/jobs/conversation/{self.worker_user.id}/'), 'tel:')
        self.assertEqual(self.client_c.get(f'/api/messages/{self.worker_user.id}/').json()['other_user']['phone_number'], '')


class GapFixTests(FlowBase):
    """Gaps found in the Nov 2026 website review."""

    def test_admin_created_from_manage_users_can_open_the_admin_panel(self):
        r = self.admin_c.post('/dashboard/users/create/', {
            'email': 'new.admin@t.co', 'password': PW, 'first_name': 'New', 'last_name': 'Admin',
            'phone_number': '+255700000001', 'user_type': 'admin', 'is_active': 'on'})
        self.assertEqual(r.status_code, 302)
        new = User.objects.get(email='new.admin@t.co')
        self.assertTrue(new.is_staff)
        c = Client(); c.force_login(new)
        self.assertEqual(c.get('/dashboard/', secure=True).status_code, 200)

    def test_staff_cannot_edit_or_delete_a_superuser(self):
        staff = User.objects.create_user(email='staff@t.co', username='staff', password=PW,
                                         user_type='admin', is_staff=True)
        c = Client(); c.force_login(staff)
        c.post(f'/dashboard/users/{self.admin.id}/edit/', {
            'email': 'hijack@t.co', 'first_name': 'X', 'last_name': 'Y',
            'phone_number': '1', 'password': 'Hijacked-2026'})
        c.post(f'/dashboard/users/{self.admin.id}/delete/')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, 'admin@t.co')
        self.assertTrue(self.admin.check_password(PW))

    def test_rejected_worker_goes_back_to_review_after_new_upload(self):
        self.wp.verification_status = 'rejected'; self.wp.save()
        r = self.worker_c.post('/api/workers/documents/upload/', {
            'document_type': 'id', 'file': SimpleUploadedFile('id.png', PNG, 'image/png')})
        self.assertEqual(r.status_code, 201, r.content)
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.verification_status, 'pending')

    def test_job_list_ignores_unknown_sort(self):
        for sort in ('foo', 'client__password', '-budget'):
            self.assertEqual(self.worker_c.get('/jobs/', {'sort': sort}, secure=True).status_code, 200, sort)

    def test_worker_can_open_an_open_job_from_browse_without_private_details(self):
        sr, _ = self.book()
        r = self.worker_c.get(f'/api/jobs/jobs/{sr.id}/')
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body['title'], 'Leaky tap')
        for private in ('location', 'client_phone', 'client_email', 'payment_transaction_id', 'admin_notes'):
            self.assertNotIn(private, body)
        # another client still cannot read it
        other = Client(); other.force_login(self.other_client)
        self.assertEqual(other.get(f'/api/jobs/jobs/{sr.id}/').status_code, 404)

    def test_direct_booking_notifies_worker_then_client(self):
        from jobs.models import DirectHireRequest
        from worker_connect.notification_models import Notification
        b = DirectHireRequest.objects.create(client=self.client_user, worker=self.wp, title='Paint wall',
                                             description='x', location='Dar', duration_value=1,
                                             start_datetime=timezone.now(), offered_rate=D('1000'),
                                             total_amount=D('1000'))
        from worker_connect.notification_service import NotificationService
        NotificationService.notify_direct_hire(b)
        self.assertIn(b.id, [n.extra_data.get('direct_hire_id')
                             for n in Notification.objects.filter(recipient=self.worker_user)])
        r = post_json(self.worker_c, f'/api/jobs/worker/direct-hire-requests/{b.id}/accept/')
        self.assertEqual(r.status_code, 200, r.content)
        n = Notification.objects.get(recipient=self.client_user, notification_type='job_accepted')
        self.assertEqual(n.target_url, f'/jobs/direct-hire/{b.id}/')
