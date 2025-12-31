"""
Celery tasks for jobs app.
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_overdue_invoices(self):
    """
    Check for overdue invoices and update their status.
    """
    try:
        from jobs.invoices import InvoiceService
        InvoiceService.check_overdue_invoices()
        logger.info("Checked overdue invoices")
    except Exception as e:
        logger.error(f"Error checking overdue invoices: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_job_reminders(self):
    """
    Send reminders for upcoming jobs.
    """
    try:
        from jobs.models import JobRequest
        from datetime import timedelta
        
        tomorrow = timezone.now().date() + timedelta(days=1)
        
        # Find jobs starting tomorrow
        upcoming_jobs = JobRequest.objects.filter(
            status='assigned',
            scheduled_date=tomorrow
        ).select_related('client__user', 'assigned_workers')
        
        for job in upcoming_jobs:
            # Send reminder to client
            send_job_reminder_email.delay(
                job.client.user.email,
                job.title,
                str(job.scheduled_date),
                'client'
            )
            
            # Send reminder to assigned workers
            for worker in job.assigned_workers.all():
                send_job_reminder_email.delay(
                    worker.user.email,
                    job.title,
                    str(job.scheduled_date),
                    'worker'
                )
        
        logger.info(f"Sent reminders for {upcoming_jobs.count()} jobs")
    except Exception as e:
        logger.error(f"Error sending job reminders: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_job_reminder_email(self, email, job_title, job_date, user_type):
    """
    Send a job reminder email.
    """
    try:
        subject = f"Reminder: {job_title} scheduled for {job_date}"
        
        context = {
            'job_title': job_title,
            'job_date': job_date,
            'user_type': user_type,
        }
        
        html_message = render_to_string('emails/job_reminder.html', context)
        
        send_mail(
            subject=subject,
            message=f"Reminder: Your job '{job_title}' is scheduled for {job_date}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent job reminder to {email}")
    except Exception as e:
        logger.error(f"Error sending job reminder email: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def cleanup_old_activities(self):
    """
    Clean up old activity entries.
    """
    try:
        from jobs.activity import ActivityService
        deleted = ActivityService.delete_old_activities(days=90)
        logger.info(f"Cleaned up old activities: {deleted}")
    except Exception as e:
        logger.error(f"Error cleaning up activities: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_application_notification(self, client_email, worker_name, job_title, job_id):
    """
    Send notification email for new job application.
    """
    try:
        subject = f"New Application for: {job_title}"
        
        context = {
            'worker_name': worker_name,
            'job_title': job_title,
            'job_id': job_id,
            'application_url': f"{settings.FRONTEND_URL}/jobs/{job_id}/applications",
        }
        
        html_message = render_to_string('emails/job_application.html', context)
        
        send_mail(
            subject=subject,
            message=f"{worker_name} has applied to your job: {job_title}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[client_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent application notification to {client_email}")
    except Exception as e:
        logger.error(f"Error sending application notification: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_assignment_notification(self, worker_email, job_title, client_name, job_id):
    """
    Send notification email for job assignment.
    """
    try:
        subject = f"You've been assigned to: {job_title}"
        
        context = {
            'worker_name': worker_email.split('@')[0],  # Fallback name
            'job_title': job_title,
            'client_name': client_name,
            'job_url': f"{settings.FRONTEND_URL}/jobs/{job_id}",
        }
        
        html_message = render_to_string('emails/job_assigned.html', context)
        
        send_mail(
            subject=subject,
            message=f"You have been assigned to the job: {job_title} by {client_name}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[worker_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent assignment notification to {worker_email}")
    except Exception as e:
        logger.error(f"Error sending assignment notification: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_review_notification(self, user_email, reviewer_name, rating, job_title):
    """
    Send notification email for new review.
    """
    try:
        subject = f"You received a {rating}-star review!"
        
        context = {
            'reviewer_name': reviewer_name,
            'rating': rating,
            'job_title': job_title,
            'review_url': f"{settings.FRONTEND_URL}/reviews",
        }
        
        html_message = render_to_string('emails/review_received.html', context)
        
        send_mail(
            subject=subject,
            message=f"{reviewer_name} left you a {rating}-star review for: {job_title}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent review notification to {user_email}")
    except Exception as e:
        logger.error(f"Error sending review notification: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_invoice_email(self, client_email, invoice_id):
    """
    Send invoice email to client.
    """
    try:
        from jobs.invoices import Invoice, InvoiceService
        
        invoice = Invoice.objects.select_related(
            'worker__user', 'client__user', 'job'
        ).get(id=invoice_id)
        
        subject = f"Invoice #{invoice.invoice_number} from Worker Connect"
        
        context = {
            'invoice': invoice,
            'client_name': invoice.client.user.get_full_name(),
            'worker_name': invoice.worker.user.get_full_name(),
            'invoice_url': f"{settings.FRONTEND_URL}/invoices/{invoice.id}",
            'payment_url': f"{settings.FRONTEND_URL}/invoices/{invoice.id}/pay",
        }
        
        html_message = render_to_string('emails/invoice.html', context)
        
        send_mail(
            subject=subject,
            message=f"You have received invoice #{invoice.invoice_number} for ${invoice.total}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[client_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent invoice email to {client_email}")
    except Exception as e:
        logger.error(f"Error sending invoice email: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_payment_notification(self, worker_email, amount, job_title=None):
    """
    Send payment received notification.
    """
    try:
        subject = f"Payment Received: ${amount}"
        
        context = {
            'worker_name': worker_email.split('@')[0],
            'amount': amount,
            'job_title': job_title,
            'earnings_url': f"{settings.FRONTEND_URL}/earnings",
        }
        
        html_message = render_to_string('emails/payment_received.html', context)
        
        send_mail(
            subject=subject,
            message=f"You have received a payment of ${amount}" + (f" for: {job_title}" if job_title else ""),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[worker_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent payment notification to {worker_email}")
    except Exception as e:
        logger.error(f"Error sending payment notification: {e}")
        raise self.retry(exc=e)


@shared_task
def log_activity(user_id, activity_type, title, description='', related_object_type=None, related_object_id=None, is_public=False):
    """
    Log an activity asynchronously.
    """
    try:
        from jobs.activity import Activity
        from django.contrib.auth import get_user_model
        from django.contrib.contenttypes.models import ContentType
        
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        activity_data = {
            'user': user,
            'activity_type': activity_type,
            'title': title,
            'description': description,
            'is_public': is_public,
        }
        
        if related_object_type and related_object_id:
            content_type = ContentType.objects.get(model=related_object_type)
            activity_data['content_type'] = content_type
            activity_data['object_id'] = related_object_id
        
        Activity.objects.create(**activity_data)
        logger.info(f"Logged activity for user {user_id}: {activity_type}")
    except Exception as e:
        logger.error(f"Error logging activity: {e}")
