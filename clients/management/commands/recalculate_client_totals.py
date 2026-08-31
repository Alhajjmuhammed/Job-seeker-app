"""
Recompute every client's job and spend totals.

They were kept by a += in one of the four places a booking can be created,
so any client who booked another way never had them move. A post_save hook
on ServiceRequest maintains them now; this repairs the clients who already
exist.

    python manage.py recalculate_client_totals            # report only
    python manage.py recalculate_client_totals --write
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Recompute every client's stored job and spend totals."

    def add_arguments(self, parser):
        parser.add_argument(
            '--write', action='store_true',
            help='save the recomputed values (default is a dry run)')

    def handle(self, *args, **options):
        from clients.models import ClientProfile

        changed = 0
        for profile in ClientProfile.objects.select_related('user'):
            was_jobs = profile.total_jobs_posted
            was_spent = profile.total_spent
            profile.recalculate_totals(save=options['write'])
            if (profile.total_jobs_posted != was_jobs
                    or profile.total_spent != was_spent):
                changed += 1
                self.stdout.write(
                    f'    {profile.user.username:28} '
                    f'jobs {was_jobs} -> {profile.total_jobs_posted}   '
                    f'spent {was_spent} -> {profile.total_spent}')

        self.stdout.write(
            f'  {changed} of {ClientProfile.objects.count()} clients change')
        if not options['write']:
            self.stdout.write('  dry run - pass --write to save')
