"""
Phone push alerts (Expo). The real Expo service is never called: _post is replaced.

    python manage.py test tests.test_push_notifications
"""
import urllib.error
from datetime import time
from unittest import mock

from django.test import TestCase, override_settings

from accounts.models import User
from worker_connect import expo_push
from worker_connect.notification_models import NotificationPreference, PushToken
from worker_connect.notification_service import NotificationService

OK = {'data': [{'status': 'ok', 'id': 'x'}]}


@override_settings(EXPO_PUSH_ENABLED=True)
class PushTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(email='p@t.co', username='pushme', password='x-Pass-2026!', user_type='worker')
        self.other = User.objects.create_user(email='o@t.co', username='other', password='x-Pass-2026!', user_type='client')
        self.tok = PushToken.objects.create(user=self.u, token='ExponentPushToken[phone-1]', device_type='android')
        PushToken.objects.create(user=self.u, token='ExponentPushToken[old-phone]', device_type='android', is_active=False)
        PushToken.objects.create(user=self.other, token='ExponentPushToken[someone-else]', device_type='ios')
        # run the background task straight away
        p = mock.patch('worker_connect.tasks.send_push_for_notification.delay',
                       side_effect=lambda nid: expo_push.push_notification(nid))
        p.start()
        self.addCleanup(p.stop)

    def notify(self, ntype='message_received', **extra):
        with self.captureOnCommitCallbacks(execute=True):
            return NotificationService.create_notification(
                recipient=self.u, title='New message', message='Asha: are you coming today?',
                notification_type=ntype, extra_data=extra or {'sender_id': self.other.id}, send_email=False)

    def test_push_goes_to_the_recipients_active_phones_with_tap_data(self):
        with mock.patch.object(expo_push, '_post', return_value=OK) as post:
            n = self.notify()
        sent = post.call_args[0][0]
        self.assertEqual([m['to'] for m in sent], ['ExponentPushToken[phone-1]'])  # not old, not others
        m = sent[0]
        self.assertEqual((m['title'], m['body'], m['sound'], m['channelId']),
                         ('New message', 'Asha: are you coming today?', 'default', 'default'))
        self.assertEqual(m['data'], {'notification_id': n.pk, 'notification_type': 'message_received',
                                     'extra_data': {'sender_id': self.other.id}})

    def test_category_switched_off_means_no_push_but_alerts_still_go(self):
        NotificationPreference.objects.create(user=self.u, push_messages=False)
        with mock.patch.object(expo_push, '_post', return_value=OK) as post:
            self.notify('message_received')
            post.assert_not_called()
            self.notify('system_alert', action='open_documents')
            self.assertEqual(post.call_count, 1)

    def test_quiet_hours_hold_back_pushes(self):
        prefs = NotificationPreference.objects.create(user=self.u, quiet_hours_start=time(22, 0), quiet_hours_end=time(6, 0))
        from django.utils import timezone
        night = timezone.localtime().replace(hour=23, minute=30)
        day = timezone.localtime().replace(hour=10, minute=0)
        self.assertTrue(expo_push.in_quiet_hours(prefs, night))
        self.assertFalse(expo_push.in_quiet_hours(prefs, day))
        early = timezone.localtime().replace(hour=5, minute=0)
        self.assertTrue(expo_push.in_quiet_hours(prefs, early))

    def test_uninstalled_app_token_is_switched_off(self):
        gone = {'data': [{'status': 'error', 'message': 'not registered', 'details': {'error': 'DeviceNotRegistered'}}]}
        with mock.patch.object(expo_push, '_post', return_value=gone):
            self.notify()
        self.tok.refresh_from_db()
        self.assertFalse(self.tok.is_active)

    def test_expo_down_never_breaks_the_action(self):
        with mock.patch.object(expo_push, '_post', side_effect=urllib.error.URLError('down')):
            n = self.notify()
        self.assertIsNotNone(n.pk)  # the notification itself is saved

    def test_no_phone_no_task(self):
        PushToken.objects.filter(user=self.u).delete()
        with mock.patch('worker_connect.tasks.send_push_for_notification.delay') as delay:
            self.notify()
        delay.assert_not_called()

    @override_settings(EXPO_PUSH_ENABLED=False)
    def test_switch_off_in_settings(self):
        with mock.patch.object(expo_push, '_post', return_value=OK) as post:
            self.notify()
        post.assert_not_called()

    def test_real_flow_sends_a_push(self):
        """A real action (a worker gets a booking request) pushes to the worker's phone."""
        from datetime import timedelta
        from decimal import Decimal
        from django.utils import timezone
        from jobs.models import DirectHireRequest
        from workers.models import WorkerProfile
        wp = WorkerProfile.objects.create(user=self.u, verification_status='verified')
        with mock.patch.object(expo_push, '_post', return_value=OK) as post, self.captureOnCommitCallbacks(execute=True):
            hire = DirectHireRequest.objects.create(
                client=self.other, worker=wp, title='Paint', description='x', location='x', duration_type='hours',
                duration_value=2, start_datetime=timezone.now() + timedelta(days=1), offered_rate=Decimal('5000'))
            NotificationService.notify_direct_hire(hire)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args[0][0][0]['data']['extra_data'].get('direct_hire_id'), hire.id)
