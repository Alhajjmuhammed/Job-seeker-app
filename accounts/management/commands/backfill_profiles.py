"""
Create the role profile for any account that is missing one.

Web client registration did not create a ClientProfile for a while, so anyone
who signed up through the website in that period has an account but no
profile. Five places reach for client_profile directly, so those users hit
errors on booking, invoices and their own profile page.

The registration forms all create profiles now; this repairs the accounts
created before that fix.

    python manage.py backfill_profiles            # report only
    python manage.py backfill_profiles --write    # create the missing rows
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Create role profiles for accounts that are missing one.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--write', action='store_true',
            help='actually create the profiles (default is a dry run)')

    def handle(self, *args, **options):
        from accounts.models import User
        from clients.models import ClientProfile
        from workers.models import WorkerProfile
        from agents.models import AgentProfile

        roles = (
            ('client', ClientProfile),
            ('worker', WorkerProfile),
            ('agent', AgentProfile),
        )

        created = 0
        for user_type, model in roles:
            missing = [
                u for u in User.objects.filter(user_type=user_type)
                if not model.objects.filter(user=u).exists()
            ]
            if not missing:
                self.stdout.write(f'  {user_type}: none missing')
                continue

            self.stdout.write(
                f'  {user_type}: {len(missing)} account(s) without a profile')
            for user in missing:
                self.stdout.write(
                    f'    {user.username}  <{user.email}>  '
                    f'joined {user.date_joined:%Y-%m-%d}')
                if options['write']:
                    with transaction.atomic():
                        model.objects.create(user=user)
                    created += 1

        if options['write']:
            self.stdout.write(self.style.SUCCESS(
                f'  created {created} profile(s)'))
        else:
            self.stdout.write(
                '  dry run - pass --write to create them')
