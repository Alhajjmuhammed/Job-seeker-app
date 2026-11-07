"""Daily upkeep for job posts: close jobs past their closing date, finish
contracts past their end date, remind both sides a week before a contract
ends. Safe to run more than once a day (cron or Celery beat)."""
from django.core.management.base import BaseCommand

from jobs.vacancy_service import daily_maintenance


class Command(BaseCommand):
    help = 'Close expired job posts, finish ended contracts, send contract-ending reminders.'

    def handle(self, *args, **options):
        result = daily_maintenance()
        self.stdout.write(f"closed {result['closed']} job post(s), finished {result['finished']} contract(s), "
                          f"sent {result['reminded']} reminder(s)")
