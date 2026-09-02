"""
Remove accounts created by deployment verification.

Verifying a deploy against the live site left a couple of throwaway client
accounts behind. They are identified by an @test.local email, which no real
user can have, and the command refuses to touch anything that has actual
activity - a service request, an assignment or a payment - so a real
account cannot be caught by a careless filter.

    python manage.py remove_test_accounts            # report only
    python manage.py remove_test_accounts --write
"""
from django.core.management.base import BaseCommand
from django.db import transaction

TEST_EMAIL_SUFFIX = '@test.local'


class Command(BaseCommand):
    help = 'Remove leftover @test.local verification accounts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--write', action='store_true',
            help='actually delete them (default is a dry run)')

    def handle(self, *args, **options):
        from accounts.models import User
        from jobs.service_request_models import (
            ServiceRequest, ServiceRequestAssignment)
        from clients.models import PaymentTransaction

        candidates = User.objects.filter(email__iendswith=TEST_EMAIL_SUFFIX)
        if not candidates.exists():
            self.stdout.write('  no @test.local accounts found')
            return

        deletable, kept = [], []
        for user in candidates:
            reasons = []
            if ServiceRequest.objects.filter(client=user).exists():
                reasons.append('has service requests')
            if hasattr(user, 'worker_profile') and ServiceRequestAssignment.objects.filter(
                    worker=user.worker_profile).exists():
                reasons.append('has assignments')
            if PaymentTransaction.objects.filter(client=user).exists():
                reasons.append('has payment records')
            if user.is_staff or user.is_superuser:
                reasons.append('is staff')
            (kept if reasons else deletable).append((user, reasons))

        for user, reasons in kept:
            self.stdout.write(self.style.WARNING(
                f'    KEEPING {user.username} <{user.email}> - '
                f'{", ".join(reasons)}'))
        for user, _ in deletable:
            self.stdout.write(
                f'    {user.username:26} <{user.email}>  '
                f'joined {user.date_joined:%Y-%m-%d}')

        if not options['write']:
            self.stdout.write(
                f'  {len(deletable)} would be removed, {len(kept)} kept'
                '  (dry run - pass --write)')
            return

        with transaction.atomic():
            removed = 0
            for user, _ in deletable:
                user.delete()
                removed += 1
        self.stdout.write(self.style.SUCCESS(
            f'  removed {removed} account(s); kept {len(kept)}'))
