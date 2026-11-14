"""
The public "delete my account" page that Google Play requires.

    python manage.py test tests.test_account_deletion_page
"""
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase

from accounts.models import User

URL = '/account/delete/'
PW = 'Str0ng-pass-2026'


class AccountDeletionPageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email='bye@t.co', username='byebye', password=PW, user_type='client')

    def test_page_is_public_and_linked_from_privacy(self):
        r = Client().get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Delete your Worker Search account')
        self.assertContains(Client().get('/privacy/'), '/account/delete/')

    def test_signed_in_wrong_password_keeps_the_account(self):
        c = Client(); c.force_login(self.user)
        c.post(URL, {'password': 'nope', 'confirm': 'on'})
        self.assertTrue(User.objects.filter(pk=self.user.pk, is_active=True).exists())

    def test_signed_in_with_password_deletes_and_signs_out(self):
        c = Client(); c.force_login(self.user)
        r = c.post(URL, {'password': PW, 'confirm': 'on'})
        self.assertEqual(r.status_code, 302)
        gone = not User.objects.filter(pk=self.user.pk).exists()
        anon = User.objects.filter(pk=self.user.pk).exclude(email='bye@t.co').exists()
        self.assertTrue(gone or anon, 'account must be deleted or anonymised')
        self.assertNotIn('_auth_user_id', c.session)

    def test_staff_cannot_delete_themselves_here(self):
        staff = User.objects.create_user(email='s@t.co', username='staffer', password=PW, user_type='admin', is_staff=True)
        c = Client(); c.force_login(staff)
        c.post(URL, {'password': PW, 'confirm': 'on'})
        self.assertTrue(User.objects.filter(pk=staff.pk, email='s@t.co').exists())

    def test_signed_out_request_emails_the_team_without_revealing_accounts(self):
        r = Client().post(URL, {'contact': 'bye@t.co', 'note': 'please delete'}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('bye@t.co', mail.outbox[0].body)
        unknown = Client().post(URL, {'contact': 'nobody@nowhere.tz'}, follow=True)
        self.assertEqual(unknown.status_code, 200)  # same answer whether or not the account exists
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())  # a request never deletes by itself

    def test_requests_are_limited(self):
        c = Client()
        for _ in range(7):
            c.post(URL, {'contact': 'x@t.co'})
        self.assertEqual(len(mail.outbox), 5)
