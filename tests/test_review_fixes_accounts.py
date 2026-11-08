"""
Fixes from the component review: accounts, admin panel, notifications.
Each test is one defect the reviewer reproduced.
"""
from decimal import Decimal as D

from django.core import mail
from django.core.cache import cache
from django.test import Client, override_settings
from rest_framework.authtoken.models import Token

from accounts.models import User
from agents.models import AgentProfile
from workers.models import Category, WorkerDocument, WorkerProfile

from .test_full_flows import PNG, PW, FlowBase, post_json


class AccountsFixTests(FlowBase):
    def app_token(self, email=None, password=PW):
        r = post_json(Client(), '/api/auth/login/', {'email': email or 'worker@t.co', 'password': password})
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()['token']

    def test_app_password_change_works_without_confirm_field(self):
        token = self.app_token()
        c = Client(HTTP_AUTHORIZATION=f'Token {token}')
        r = post_json(c, '/api/auth/change-password/', {'current_password': PW, 'new_password': 'Brand-new-pass-2026'})
        self.assertEqual(r.status_code, 200, r.content)
        self.worker_user.refresh_from_db()
        self.assertTrue(self.worker_user.check_password('Brand-new-pass-2026'))
        # a mismatching confirm (when sent) is still refused
        r = post_json(c, '/api/auth/change-password/', {'current_password': 'Brand-new-pass-2026',
                                                       'new_password': 'Another-pass-2026',
                                                       'new_password_confirm': 'different-2026'})
        self.assertEqual(r.status_code, 400)

    def test_change_password_from_a_browser_session_does_not_crash(self):
        r = post_json(self.worker_c, '/api/auth/change-password/', {'current_password': PW,
                                                                    'new_password': 'Brand-new-pass-2026'})
        self.assertEqual(r.status_code, 200, r.content)

    def test_each_limit_has_its_own_counter(self):
        from accounts.api_views import LoginRateThrottle, PasswordResetThrottle, RegisterRateThrottle
        scopes = {LoginRateThrottle.scope, RegisterRateThrottle.scope, PasswordResetThrottle.scope}
        self.assertEqual(len(scopes), 3)
        self.assertNotIn('anon', scopes)

    @override_settings(LOGIN_FAILURE_LIMIT=3)
    def test_app_login_locks_out_after_repeated_failures(self):
        cache.clear()
        for _ in range(3):
            r = post_json(Client(), '/api/auth/login/', {'email': 'worker@t.co', 'password': 'wrong'})
            self.assertEqual(r.status_code, 401)
        r = post_json(Client(), '/api/auth/login/', {'email': 'worker@t.co', 'password': PW})
        self.assertEqual(r.status_code, 429)  # even the right password waits out the lockout

    def test_forgot_password_is_rate_limited_per_address(self):
        cache.clear()
        mail.outbox.clear()
        for _ in range(5):
            Client(REMOTE_ADDR='10.9.9.%d' % _).post('/accounts/forgot-password/', {'email': 'worker@t.co'}, secure=True)
        self.assertEqual(len(mail.outbox), 3)

    @override_settings(EMAIL_BACKEND='tests.broken_mail.Broken')
    def test_forgot_password_never_500s_on_a_mail_error(self):
        cache.clear()
        r = Client().post('/accounts/forgot-password/', {'email': 'worker@t.co'}, secure=True)
        self.assertEqual(r.status_code, 302)  # same answer as for an unknown email

    def test_password_reset_signs_out_the_app(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        self.app_token()
        self.assertTrue(Token.objects.filter(user=self.worker_user).exists())
        uid = urlsafe_base64_encode(force_bytes(self.worker_user.pk))
        tok = default_token_generator.make_token(self.worker_user)
        Client().post(f'/accounts/reset-password/{uid}/{tok}/',
                      {'password1': 'Reset-pass-2026!', 'password2': 'Reset-pass-2026!'}, secure=True)
        self.worker_user.refresh_from_db()
        self.assertTrue(self.worker_user.check_password('Reset-pass-2026!'))
        self.assertFalse(Token.objects.filter(user=self.worker_user).exists())

    def test_anonymise_removes_id_documents(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from accounts.gdpr import GDPRService
        WorkerDocument.objects.create(worker=self.wp, document_type='id', title='ID',
                                      file=SimpleUploadedFile('id.png', PNG, 'image/png'))
        GDPRService.anonymize_user(self.worker_user)
        self.assertFalse(WorkerDocument.objects.filter(worker=self.wp).exists())

    def test_quiet_hours_bad_time_is_a_400(self):
        r = post_json(self.worker_c, '/api/v1/notification-preferences/quiet-hours/',
                      {'enabled': True, 'start': '10pm', 'end': '07:00'})
        self.assertEqual(r.status_code, 400, r.content)


class AdminPanelFixTests(FlowBase):
    def test_deactivated_worker_leaves_the_assign_lists(self):
        self.admin_c.post(f'/dashboard/users/{self.worker_user.id}/toggle-status/', secure=True)
        self.wp.refresh_from_db(); self.worker_user.refresh_from_db()
        self.assertEqual((self.worker_user.is_active, self.wp.availability), (False, 'offline'))

    def test_staff_cannot_deactivate_a_superuser(self):
        staff = User.objects.create_user(email='staff2@t.co', username='staff2', password=PW,
                                         user_type='admin', is_staff=True)
        c = Client(); c.force_login(staff)
        c.post(f'/dashboard/users/{self.admin.id}/toggle-status/', secure=True)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_category_counts_are_not_multiplied(self):
        from jobs.service_request_models import ServiceRequest
        for i in range(3):
            ServiceRequest.objects.create(client=self.client_user, category=self.cat, title=f'r{i}', description='x',
                                          location='x', city='Dar', preferred_date='2026-12-01')
        r = self.admin_c.get('/dashboard/categories/', secure=True)
        cat = [c for c in r.context['categories'] if c.pk == self.cat.pk][0]
        self.assertEqual((cat.worker_count, cat.job_count), (2, 3))

    def test_bad_input_does_not_crash_admin_pages(self):
        self.assertEqual(self.admin_c.get('/dashboard/reports/?days=abc', secure=True).status_code, 200)
        other = Category.objects.create(name='Painter', daily_rate=D('1'), service_fee=D('1'))
        r = self.admin_c.post('/dashboard/categories/', {'action': 'edit', 'category_id': other.id, 'name': 'plumber'},
                              secure=True)
        self.assertEqual(r.status_code, 302)
        other.refresh_from_db(); self.assertEqual(other.name, 'Painter')
        r = self.admin_c.post('/dashboard/categories/', {'action': 'delete', 'category_id': 'abc'}, secure=True)
        self.assertEqual(r.status_code, 302)

    def test_verified_agent_cannot_be_rejected(self):
        self.admin_c.post(f'/dashboard/agents/{self.agent.id}/reject/', secure=True)
        self.assertTrue(AgentProfile.objects.filter(pk=self.agent.pk).exists())

    def test_bulk_verify_needs_an_approved_id(self):
        u = User.objects.create_user(email='noid@t.co', username='noid', password=PW, user_type='worker')
        noid = WorkerProfile.objects.create(user=u, verification_status='pending')
        r = post_json(self.admin_c, '/api/v1/admin/bulk/workers/', {'worker_ids': [noid.id], 'action': 'verify'})
        self.assertIn(r.status_code, (200, 201), r.content)
        noid.refresh_from_db()
        self.assertEqual(noid.verification_status, 'pending')

    def test_editing_a_user_keeps_their_username(self):
        self.admin_c.post(f'/dashboard/users/{self.agent_user.id}/edit/', {
            'email': 'agent@t.co', 'first_name': 'A', 'last_name': 'G', 'phone_number': '+255700000123',
            'is_active': 'on'}, secure=True)
        self.agent_user.refresh_from_db()
        self.assertEqual(self.agent_user.username, 'agentx')

    def test_users_list_query_count_does_not_grow_with_users(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as before:
            self.admin_c.get('/dashboard/users/', secure=True)
        for i in range(40):
            User.objects.create_user(email=f'bulk{i}@t.co', username=f'bulk{i}', password=PW, user_type='client')
        with CaptureQueriesContext(connection) as after:
            self.admin_c.get('/dashboard/users/', secure=True)
        self.assertLess(len(after) - len(before), 30, (len(before), len(after)))
