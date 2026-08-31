"""
Recompute profile completion for every worker.

is_profile_complete was never written by any code path, so it was False for
every worker on the platform while several features gated on it. The
percentage was only recalculated when a document was uploaded, so workers
who registered through the website sat at 0% however much they had filled
in. WorkerProfile.recalculate_completion() decides both now; this applies it
to the workers who already exist.

    python manage.py recalculate_completion            # report only
    python manage.py recalculate_completion --write
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Recompute profile completion for every worker.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--write', action='store_true',
            help='save the recomputed values (default is a dry run)')

    def handle(self, *args, **options):
        from workers.models import WorkerProfile

        became_complete = changed = 0
        profiles = WorkerProfile.objects.prefetch_related('categories', 'documents')
        for profile in profiles:
            was_percentage = profile.profile_completion_percentage
            was_complete = profile.is_profile_complete
            profile.recalculate_completion(save=options['write'])
            if (profile.profile_completion_percentage != was_percentage
                    or profile.is_profile_complete != was_complete):
                changed += 1
                if profile.is_profile_complete and not was_complete:
                    became_complete += 1
                self.stdout.write(
                    f'    {profile.user.username:26} '
                    f'{was_percentage}% -> {profile.profile_completion_percentage}%'
                    f'   complete {was_complete} -> {profile.is_profile_complete}')

        self.stdout.write(
            f'  {changed} of {WorkerProfile.objects.count()} profiles change; '
            f'{became_complete} become complete')
        if not options['write']:
            self.stdout.write('  dry run - pass --write to save')
