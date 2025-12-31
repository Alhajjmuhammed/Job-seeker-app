"""
Admin notification utilities for Worker Connect.

This module provides utility functions for sending notifications to admins
about important system events like new user registrations, job postings,
reports, etc.
"""
from django.core.mail import send_mail, mail_admins
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger('api')


def notify_admins_new_user(user):
    """
    Send notification to admins when a new user registers.
    
    Args:
        user: The newly registered User instance
    """
    try:
        subject = f'New User Registration: {user.email}'
        message = f"""
A new user has registered on Worker Connect:

Name: {user.first_name} {user.last_name}
Email: {user.email}
User Type: {user.user_type}
Phone: {user.phone_number or 'Not provided'}
Registered: {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}

Please review the account if verification is required.
        """
        
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=True
        )
        logger.info(f"Admin notification sent for new user: {user.email}")
    except Exception as e:
        logger.error(f"Failed to send admin notification for new user: {str(e)}")


def notify_admins_new_job(job):
    """
    Send notification to admins when a new job is posted.
    
    Args:
        job: The newly created JobRequest instance
    """
    try:
        subject = f'New Job Posted: {job.title}'
        message = f"""
A new job has been posted on Worker Connect:

Title: {job.title}
Client: {job.client.email}
Category: {job.category.name if job.category else 'Not specified'}
City: {job.city}
Budget: ${job.budget or 'Not specified'}
Duration: {job.duration_days} days
Urgency: {job.urgency}

Posted: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=True
        )
        logger.info(f"Admin notification sent for new job: {job.title}")
    except Exception as e:
        logger.error(f"Failed to send admin notification for new job: {str(e)}")


def notify_admins_verification_request(worker_profile):
    """
    Send notification to admins when a worker requests verification.
    
    Args:
        worker_profile: The WorkerProfile instance requesting verification
    """
    try:
        subject = f'Verification Request: {worker_profile.user.email}'
        message = f"""
A worker has requested profile verification:

Worker: {worker_profile.user.first_name} {worker_profile.user.last_name}
Email: {worker_profile.user.email}
Worker Type: {worker_profile.worker_type}
Experience: {worker_profile.years_experience or 0} years

Please review the submitted documents and verify or reject the profile.
        """
        
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=True
        )
        logger.info(f"Admin notification sent for verification request: {worker_profile.user.email}")
    except Exception as e:
        logger.error(f"Failed to send admin notification for verification: {str(e)}")


def notify_admins_report(report_type, reported_by, reported_item, reason):
    """
    Send notification to admins when something is reported.
    
    Args:
        report_type: Type of report (e.g., 'user', 'job', 'review')
        reported_by: User who submitted the report
        reported_item: The item being reported
        reason: Reason for the report
    """
    try:
        subject = f'New Report: {report_type}'
        message = f"""
A new report has been submitted:

Report Type: {report_type}
Reported By: {reported_by.email}
Reason: {reason}

Item Details:
{str(reported_item)}

Please review and take appropriate action.
        """
        
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=True
        )
        logger.info(f"Admin notification sent for report by: {reported_by.email}")
    except Exception as e:
        logger.error(f"Failed to send admin notification for report: {str(e)}")


def notify_user(user, subject, message, html_message=None):
    """
    Send email notification to a specific user.
    
    Args:
        user: User instance to send notification to
        subject: Email subject
        message: Plain text message
        html_message: Optional HTML message
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        logger.info(f"Notification sent to user: {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {user.email}: {str(e)}")
        return False


def notify_job_application_received(application):
    """
    Send notification to client when a worker applies for their job.
    
    Args:
        application: JobApplication instance
    """
    try:
        job = application.job
        worker = application.worker.user
        client = job.client
        
        subject = f'New Application for: {job.title}'
        message = f"""
Hello {client.first_name},

You have received a new application for your job posting "{job.title}".

Applicant: {worker.first_name} {worker.last_name}
Email: {worker.email}

Log in to review the application and respond.

Best regards,
Worker Connect Team
        """
        
        notify_user(client, subject, message)
        logger.info(f"Application notification sent to client: {client.email}")
    except Exception as e:
        logger.error(f"Failed to send application notification: {str(e)}")


def notify_application_status_change(application):
    """
    Send notification to worker when their application status changes.
    
    Args:
        application: JobApplication instance with updated status
    """
    try:
        job = application.job
        worker = application.worker.user
        
        status_messages = {
            'accepted': 'Congratulations! Your application has been accepted.',
            'rejected': 'Unfortunately, your application was not selected.',
            'shortlisted': 'Great news! You have been shortlisted for this job.',
        }
        
        status_msg = status_messages.get(
            application.status, 
            f'Your application status has been updated to: {application.status}'
        )
        
        subject = f'Application Update: {job.title}'
        message = f"""
Hello {worker.first_name},

{status_msg}

Job: {job.title}
Client: {job.client.first_name} {job.client.last_name}

Log in to view more details.

Best regards,
Worker Connect Team
        """
        
        notify_user(worker, subject, message)
        logger.info(f"Application status notification sent to: {worker.email}")
    except Exception as e:
        logger.error(f"Failed to send application status notification: {str(e)}")
