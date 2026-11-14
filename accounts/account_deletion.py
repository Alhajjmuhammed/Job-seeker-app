"""
Public "delete my account" page - https://workersearch.co.tz/account/delete/

Google Play requires a web link where anyone can ask for their account and data to
be deleted, even after removing the app. Signed in, the account is deleted here
(the same GDPRService call the app uses); signed out, the request is e-mailed to
the team, without saying whether such an account exists.
"""
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .gdpr import GDPRService
from .views import _client_ip

logger = logging.getLogger('security')

REQUESTS_PER_HOUR = 5


def account_delete(request):
    user = request.user
    signed_in = user.is_authenticated
    ctx = {'signed_in': signed_in, 'support_email': _support_email()}

    if request.method != 'POST':
        return render(request, 'account_delete.html', ctx)

    if signed_in:
        if user.is_staff or user.is_superuser:
            messages.error(request, _('Staff accounts are removed by an administrator, not from this page.'))
            return redirect('account_delete')
        if not request.POST.get('confirm'):
            messages.error(request, _('Please tick the box to confirm that you want to delete your account.'))
            return render(request, 'account_delete.html', ctx)
        if not user.check_password(request.POST.get('password', '')):
            messages.error(request, _('That password is not right.'))
            return render(request, 'account_delete.html', ctx)
        logger.info('Account deletion from the web page for user %s', user.pk)
        result = GDPRService.delete_user_data(user, confirm=True)
        if not result.get('success', True):
            messages.error(request, _('We could not delete your account. Please contact us.'))
            return render(request, 'account_delete.html', ctx)
        logout(request)
        messages.success(request, _('Your account and personal data have been deleted.'))
        return redirect('home')

    # signed out: send the request to the team
    key = f'account-delete-requests:{_client_ip(request)}'
    count = cache.get(key, 0)
    if count >= REQUESTS_PER_HOUR:
        messages.error(request, _('Too many requests. Please try again later.'))
        return render(request, 'account_delete.html', ctx)
    contact = request.POST.get('contact', '').strip()[:200]
    note = request.POST.get('note', '').strip()[:1000]
    if not contact:
        messages.error(request, _('Please enter the e-mail or phone number of your account.'))
        return render(request, 'account_delete.html', ctx)
    cache.set(key, count + 1, 3600)
    try:
        send_mail(
            subject='Account deletion request (workersearch.co.tz)',
            message=(f'Someone asked for an account to be deleted.\n\n'
                     f'Account e-mail or phone: {contact}\n'
                     f'Note: {note or "-"}\n\n'
                     f'Check that it is really their account (contact them on that e-mail/phone), '
                     f'then delete it in the admin panel within 30 days.'),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[_support_email()],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Could not e-mail an account deletion request')
    messages.success(request, _('Thank you. We received your request and will contact you to confirm, '
                                'then delete the account within 30 days.'))
    return redirect('account_delete')


def _support_email():
    return getattr(settings, 'ACCOUNT_DELETION_EMAIL', 'sales@easyfix.co.tz')
