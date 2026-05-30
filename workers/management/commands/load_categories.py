# Initial data for categories
# To load: python manage.py loaddata workers/fixtures/initial_categories.json

from django.core.management import BaseCommand
from workers.models import Category

class Command(BaseCommand):
    help = 'Load initial categories'

    def handle(self, *args, **options):
        categories = [
            {'name': 'Plumber', 'description': 'Plumbing services and repairs', 'icon': 'bi-tools'},
            {'name': 'Electrician', 'description': 'Electrical installations and repairs', 'icon': 'bi-lightning-charge'},
            {'name': 'Housekeeper', 'description': 'House cleaning and maintenance', 'icon': 'bi-house-door'},
            {'name': 'Waiter/Waitress', 'description': 'Restaurant and catering services', 'icon': 'bi-cup-hot'},
            {'name': 'Driver', 'description': 'Personal and commercial driving', 'icon': 'bi-car-front'},
            {'name': 'Painter', 'description': 'Interior and exterior painting', 'icon': 'bi-brush'},
            {'name': 'Carpenter', 'description': 'Woodwork and furniture making', 'icon': 'bi-hammer'},
            {'name': 'AC Technician', 'description': 'Air conditioning installation and repair', 'icon': 'bi-thermometer'},
            {'name': 'Gardener', 'description': 'Garden maintenance and landscaping', 'icon': 'bi-tree'},
            {'name': 'Cook', 'description': 'Professional cooking services', 'icon': 'bi-egg-fried'},
            {'name': 'Cleaner', 'description': 'General cleaning services', 'icon': 'bi-droplet'},
            {'name': 'Mechanic', 'description': 'Vehicle repair and maintenance', 'icon': 'bi-wrench'},
            {'name': 'Security Guard', 'description': 'Security and protection services', 'icon': 'bi-shield-check'},
            {'name': 'Delivery Person', 'description': 'Delivery and courier services', 'icon': 'bi-box-seam'},
            {'name': 'Nanny', 'description': 'Childcare services', 'icon': 'bi-heart'},
        ]

        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'icon': cat_data['icon'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Category already exists: {category.name}'))

        self.stdout.write(self.style.SUCCESS('\nSuccessfully loaded all categories!'))
