"""
Set the platform's service fee on service categories.

The fee is what the platform keeps on a booking: a request is priced
(daily_rate x workers_needed) + service_fee, and the workers are paid the
daily_rate. A category whose fee is zero earns the platform nothing, which
is how all 95 of them shipped.

Existing service requests are deliberately left alone. Each one stores the
fee it was booked at, and a price a client already agreed to must not change
underneath them.

    python manage.py set_service_fee 30000            # report only
    python manage.py set_service_fee 30000 --write
    python manage.py set_service_fee 30000 --write --only-zero
"""
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Set the platform service fee on every service category."

    def add_arguments(self, parser):
        parser.add_argument('amount', help='the fee, e.g. 30000')
        parser.add_argument(
            '--write', action='store_true',
            help='actually save (default is a dry run)')
        parser.add_argument(
            '--only-zero', action='store_true',
            help='leave categories that already have a fee set')

    def handle(self, *args, **options):
        from jobs.models import Category

        try:
            amount = Decimal(str(options['amount']))
        except (InvalidOperation, ValueError):
            raise CommandError(f"{options['amount']!r} is not a number")
        if amount < 0:
            raise CommandError('the fee cannot be negative')

        categories = Category.objects.all()
        if options['only_zero']:
            categories = categories.filter(service_fee=0)

        changing = [c for c in categories if c.service_fee != amount]
        self.stdout.write(
            f'  {len(changing)} of {Category.objects.count()} categories '
            f'would change to {amount}')
        for category in changing[:5]:
            self.stdout.write(
                f'    {category.name:32} {category.service_fee} -> {amount}'
                f'   (daily_rate {category.daily_rate})')
        if len(changing) > 5:
            self.stdout.write(f'    ... and {len(changing) - 5} more')

        if not options['write']:
            self.stdout.write('  dry run - pass --write to apply')
            return

        with transaction.atomic():
            updated = categories.update(service_fee=amount)
        self.stdout.write(self.style.SUCCESS(
            f'  set service_fee to {amount} on {updated} categories'))
        self.stdout.write(
            '  existing service requests keep the fee they were booked at')
