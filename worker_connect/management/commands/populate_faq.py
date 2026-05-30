from django.core.management.base import BaseCommand
from worker_connect.support_models import FAQ


class Command(BaseCommand):
    help = 'Populate FAQ data'

    def handle(self, *args, **options):
        faqs = [
            {
                'category': 'general',
                'question': 'How does Worker Connect work?',
                'answer': 'Worker Connect is a platform that connects clients with skilled workers for various services.',
            },
            {
                'category': 'worker',
                'question': 'How do I become a worker?',
                'answer': 'Create an account, complete your profile, upload required documents, and start applying for jobs.',
            },
            {
                'category': 'client',
                'question': 'How do I request a service?',
                'answer': 'Browse available services, select a category, and submit your job request with details.',
            },
            {
                'category': 'payment',
                'question': 'How do payments work?',
                'answer': 'Payments are processed securely through our platform after job completion.',
            },
            {
                'category': 'technical',
                'question': 'What if I encounter a technical issue?',
                'answer': 'Contact our support team through the app or email support@workerconnect.com.',
            },
        ]

        for faq_data in faqs:
            faq, created = FAQ.objects.get_or_create(
                category=faq_data['category'],
                question=faq_data['question'],
                defaults={
                    'answer': faq_data['answer'],
                    'is_active': True,
                    'order': 0
                }
            )
            if created:
                self.stdout.write(f'Created FAQ: {faq.question}')
            else:
                self.stdout.write(f'FAQ already exists: {faq.question}')