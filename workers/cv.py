"""
Auto-generated CV/resume for workers, built from their existing profile data.
"""

from django.template.loader import render_to_string


class CVService:
    """
    Builds a CV from a worker's existing profile data (bio, experience,
    skills, categories) - no separate CV model or upload required.
    """

    @staticmethod
    def get_cv_context(worker):
        """Assemble the display data for a worker's CV."""
        user = worker.user

        location_parts = [p for p in [worker.city, worker.state, worker.country] if p]

        categories = list(worker.categories.all()) + list(worker.custom_categories.all())

        skills = list(worker.skills.all()) + list(worker.custom_skills.all())

        experiences = worker.experiences.all().order_by('-start_date')

        is_complete = bool(
            worker.bio and worker.city and categories and (skills or experiences)
        )

        return {
            'worker': worker,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'location': ', '.join(location_parts),
            'bio': worker.bio,
            'worker_type': worker.get_worker_type_display(),
            'experience_years': worker.experience_years,
            'hourly_rate': worker.hourly_rate,
            'average_rating': worker.average_rating,
            'completed_jobs': worker.completed_jobs,
            'verification_status': worker.verification_status,
            'categories': categories,
            'skills': skills,
            'experiences': experiences,
            'profile_image_url': worker.profile_image.url if worker.profile_image else None,
            'is_complete': is_complete,
        }

    @staticmethod
    def generate_pdf(worker):
        """
        Generate the CV as PDF bytes. Returns None if PDF generation
        isn't available (mirrors InvoiceService.generate_pdf).
        """
        try:
            from weasyprint import HTML

            context = CVService.get_cv_context(worker)
            html_content = render_to_string('workers/cv_template.html', context)
            return HTML(string=html_content).write_pdf()

        except ImportError:
            return None
