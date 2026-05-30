from django.core.management.base import BaseCommand
from workers.models import Category, Skill


class Command(BaseCommand):
    help = 'Populate skills for all categories'

    def handle(self, *args, **options):
        # Skills organized by category
        category_skills = {
            'Plumber': [
                'Pipe Installation', 'Leak Repair', 'Drain Cleaning', 
                'Water Heater Installation', 'Bathroom Fitting', 'Pipe Welding',
                'Sewer Line Repair', 'Fixture Installation', 'Gas Pipe Installation'
            ],
            'Electrician': [
                'Wiring Installation', 'Circuit Repair', 'Light Fixture Installation',
                'Electrical Panel Upgrade', 'Security System Installation', 'Generator Installation',
                'Electrical Troubleshooting', 'Outlet Installation', 'Ceiling Fan Installation'
            ],
            'Carpenter': [
                'Furniture Making', 'Door Installation', 'Window Installation',
                'Cabinet Making', 'Flooring Installation', 'Roof Framing',
                'Custom Woodwork', 'Deck Building', 'Staircase Installation'
            ],
            'Painter': [
                'Interior Painting', 'Exterior Painting', 'Wall Preparation',
                'Spray Painting', 'Texture Painting', 'Wallpaper Installation',
                'Color Consulting', 'Staining & Varnishing', 'Epoxy Coating'
            ],
            'Mason': [
                'Bricklaying', 'Stone Masonry', 'Concrete Work',
                'Block Laying', 'Tile Installation', 'Plastering',
                'Foundation Work', 'Retaining Walls', 'Fireplace Construction'
            ],
            'Gardener': [
                'Lawn Mowing', 'Tree Pruning', 'Garden Design',
                'Irrigation System Installation', 'Pest Control', 'Fertilization',
                'Hedge Trimming', 'Flower Bed Maintenance', 'Composting'
            ],
            'Cleaner': [
                'House Cleaning', 'Office Cleaning', 'Deep Cleaning',
                'Carpet Cleaning', 'Window Cleaning', 'Pressure Washing',
                'Post-Construction Cleaning', 'Move-In/Out Cleaning', 'Sanitization'
            ],
            'Driver': [
                'Personal Driving', 'Delivery Services', 'Long Distance Driving',
                'Chauffeur Services', 'Vehicle Maintenance', 'Route Planning',
                'Defensive Driving', 'Commercial Driving', 'Night Driving'
            ],
            'Cook': [
                'Home Cooking', 'Meal Preparation', 'Baking',
                'Food Presentation', 'Menu Planning', 'Dietary Cooking',
                'Catering Services', 'International Cuisine', 'Food Safety'
            ],
            'Security Guard': [
                'Property Surveillance', 'Access Control', 'Patrol Services',
                'CCTV Monitoring', 'Emergency Response', 'Report Writing',
                'Crowd Control', 'Fire Safety', 'First Aid'
            ],
            'AC Technician': [
                'AC Installation', 'AC Repair', 'AC Maintenance',
                'Refrigerant Recharging', 'Duct Cleaning', 'Thermostat Installation',
                'Compressor Repair', 'Filter Replacement', 'Energy Efficiency Optimization'
            ],
        }

        created_count = 0
        skipped_count = 0
        
        for category_name, skills in category_skills.items():
            try:
                category = Category.objects.get(name=category_name)
                self.stdout.write(f"\n✅ Processing: {category_name}")
                
                for skill_name in skills:
                    skill, created = Skill.objects.get_or_create(
                        category=category,
                        name=skill_name
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {skill_name}"))
                        created_count += 1
                    else:
                        self.stdout.write(f"  - Exists: {skill_name}")
                        skipped_count += 1
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"❌ Category not found: {category_name}"))
                self.stdout.write("   Please create this category in admin first")
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Summary:"))
        self.stdout.write(self.style.SUCCESS(f"  Created: {created_count} skills"))
        self.stdout.write(f"  Skipped: {skipped_count} skills (already exist)")
        self.stdout.write("="*50)
        self.stdout.write(self.style.SUCCESS("\n✅ Done! Skills are now available in the profile edit form."))
