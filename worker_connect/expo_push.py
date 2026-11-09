"""
Phone push alerts through Expo's push service.

The app registers an Expo push token (ExponentPushToken[...]) for each phone
(POST /api/notifications/push-token/register/). Until now nothing ever sent to
those tokens: people only saw a notification when they opened the app, or by email.

Every Notification created by NotificationService now also goes to the
recipient's phones - in the background, after the database commit, following the
same per-category choices as e-mail (NotificationPreference.push_*) and the
user's quiet hours. Expo then delivers to Android (FCM) and iOS (APNs) using the
credentials stored in the app's Expo/EAS project.

Tokens Expo reports as DeviceNotRegistered (app uninstalled) are switched off.
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('api')

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'
BATCH = 100  # Expo accepts up to 100 messages per request

# Which NotificationPreference field gates a phone push for a notification_type.
# Types not listed (system_alert, document_verified, ...) always go: they are
# operational, not marketing.
NOTIFICATION_TYPE_TO_PUSH_PREF = {
    'job_assigned': 'push_job_assignments',
    'job_accepted': 'push_job_assignments',
    'job_rejected': 'push_job_assignments',
    'job_completed': 'push_job_assignments',
    'job_application': 'push_job_applications',
    'message_received': 'push_messages',
    'payment_received': 'push_payments',
    'review_received': 'push_reviews',
    'promotion': 'push_promotions',
}


def enabled():
    return bool(getattr(settings, 'EXPO_PUSH_ENABLED', False))


def in_quiet_hours(prefs, now=None):
    start, end = getattr(prefs, 'quiet_hours_start', None), getattr(prefs, 'quiet_hours_end', None)
    if not start or not end or start == end:
        return False
    t = (now or timezone.localtime()).time()  # Tanzania time
    if start < end:
        return start <= t < end
    return t >= start or t < end  # e.g. 22:00 -> 06:00


def wants_push(notification):
    """The recipient's own choices: the category switch and quiet hours."""
    from .notification_models import NotificationPreference
    prefs = NotificationPreference.objects.filter(user_id=notification.recipient_id).first()
    if prefs is None:
        return True  # defaults are "on"
    field = NOTIFICATION_TYPE_TO_PUSH_PREF.get(notification.notification_type)
    if field and not getattr(prefs, field, True):
        return False
    return not in_quiet_hours(prefs)


def build_message(notification, token):
    body = (notification.message or '').strip()
    return {
        'to': token,
        'title': (notification.title or 'Worker Connect')[:100],
        'body': body[:240] + ('…' if len(body) > 240 else ''),
        'sound': 'default',
        'priority': 'high',
        'channelId': 'default',  # the Android channel the app creates
        # what the app's tap handler reads (contexts/NotificationContext.tsx)
        'data': {
            'notification_id': notification.pk,
            'notification_type': notification.notification_type,
            'extra_data': notification.extra_data or {},
        },
    }


def _post(messages):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Accept-Encoding': 'identity'}
    token = getattr(settings, 'EXPO_ACCESS_TOKEN', '')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(EXPO_PUSH_URL, data=json.dumps(messages).encode('utf-8'),
                                 headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8') or '{}')


def send_messages(messages):
    """Send to Expo; switch off tokens that are gone. Returns (sent_ok, failed)."""
    from .notification_models import PushToken
    ok = failed = 0
    for i in range(0, len(messages), BATCH):
        chunk = messages[i:i + BATCH]
        try:
            reply = _post(chunk)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            logger.warning('Expo push request failed: %s', e)
            failed += len(chunk)
            continue
        tickets = reply.get('data') or []
        if isinstance(tickets, dict):  # a single message gets a single ticket
            tickets = [tickets]
        for msg, ticket in zip(chunk, tickets):
            if ticket.get('status') == 'ok':
                ok += 1
                continue
            failed += 1
            err = (ticket.get('details') or {}).get('error')
            if err == 'DeviceNotRegistered':
                PushToken.objects.filter(token=msg['to']).update(is_active=False)
            logger.info('Expo push not delivered (%s): %s', err, ticket.get('message'))
        if reply.get('errors'):
            logger.warning('Expo push errors: %s', reply['errors'])
    return ok, failed


def push_notification(notification_id):
    """Send one stored Notification to all of the recipient's phones."""
    from .notification_models import Notification, PushToken
    if not enabled():
        return 0, 0
    n = Notification.objects.filter(pk=notification_id).select_related('recipient').first()
    if n is None or not n.recipient.is_active:
        return 0, 0
    tokens = list(PushToken.objects.filter(user_id=n.recipient_id, is_active=True)
                  .values_list('token', flat=True))
    tokens = [t for t in tokens if t.startswith(('ExponentPushToken[', 'ExpoPushToken['))]
    if not tokens or not wants_push(n):
        return 0, 0
    return send_messages([build_message(n, t) for t in tokens])
