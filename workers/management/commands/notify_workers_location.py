"""
Ask every worker who has not saved a location to save one, so clients who
choose "nearest worker" can be matched with them.

Shows who would be notified and the message, and sends nothing, unless
--send is given:

    python manage.py notify_workers_location           # preview
    python manage.py notify_workers_location --send    # in-app + email
"""
from django.core.management.base import BaseCommand

from workers.models import WorkerProfile

TITLE = 'Get jobs near you 📍'
MESSAGE = (
    'Clients can now be matched automatically with the nearest worker. '
    'Open your Worker Connect dashboard and tap "Save my location" where you usually '
    'work, so jobs near you can reach you. It takes one tap.'
)


class Command(BaseCommand):
    help = 'Ask workers without a saved location to save one (preview unless --send).'

    def add_arguments(self, parser):
        parser.add_argument('--send', action='store_true', help='Actually send the notification.')

    def handle(self, *args, send=False, **options):
        workers = (WorkerProfile.objects
                   .filter(user__is_active=True)
                   .filter(latitude__isnull=True)
                   .select_related('user'))
        count = workers.count()

        self.stdout.write(f'Title:   {TITLE}')
        self.stdout.write(f'Message: {MESSAGE}')
        self.stdout.write(f'Workers without a location: {count}')

        if not send:
            self.stdout.write('Preview only - nothing sent. Run again with --send to send.')
            return

        from worker_connect.notification_service import NotificationService
        sent = 0
        for worker in workers:
            NotificationService.create_notification(
                recipient=worker.user,
                title=TITLE,
                message=MESSAGE,
                notification_type='system_alert',
                extra_data={'action': 'save_location'},
            )
            sent += 1
        self.stdout.write(self.style.SUCCESS(f'Sent to {sent} workers.'))
