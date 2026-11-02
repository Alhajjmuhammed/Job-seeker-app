"""
Private uploads: national IDs, payment proofs, support attachments.

nginx used to serve everything under /media/ to anyone holding the URL, so a
worker's ID card or a client's payment screenshot was public forever once a
link leaked. The private folders are now routed through Django, which checks
who is asking and hands the file back to nginx (X-Accel-Redirect) to send.
"""

import mimetypes
import os

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden

PRIVATE_MEDIA_DIRS = (
    'worker_documents',
    'payment_screenshots',
    'support_tickets',
    'cover_letters',
    'badge_verifications',
)

# Mobile opens a worker's own document in the browser, which has no login,
# so the API hands out a link signed for that one file.
_SIGNER_SALT = 'private-media'
SIGNED_URL_MAX_AGE = 60 * 60  # 1 hour


def sign_media_path(path):
    return signing.TimestampSigner(salt=_SIGNER_SALT).sign(path).split(':', 1)[1]


def signed_media_url(request, file_field):
    """Absolute URL to a private file that works without a login for an hour."""
    if not file_field:
        return None
    url = request.build_absolute_uri(file_field.url)
    return f"{url}?sig={sign_media_path(file_field.name)}"


def _signature_ok(path, sig):
    try:
        signing.TimestampSigner(salt=_SIGNER_SALT).unsign(f"{path}:{sig}", max_age=SIGNED_URL_MAX_AGE)
        return True
    except signing.BadSignature:
        return False


def _owns(user, path):
    folder = path.split('/', 1)[0]
    if folder == 'worker_documents':
        from workers.models import WorkerDocument
        return WorkerDocument.objects.filter(file=path, worker__user=user).exists()
    if folder == 'payment_screenshots':
        from jobs.service_request_models import ServiceRequest
        return ServiceRequest.objects.filter(payment_screenshot=path, client=user).exists()
    if folder == 'support_tickets':
        from worker_connect.support_models import SupportTicket
        return SupportTicket.objects.filter(attachments=path, user=user).exists()
    if folder == 'cover_letters':
        from django.db.models import Q
        from jobs.models import JobApplication
        return JobApplication.objects.filter(
            Q(worker__user=user) | Q(job__client=user), cover_letter_file=path
        ).exists()
    if folder == 'badge_verifications':
        from workers.badges import WorkerBadge
        return WorkerBadge.objects.filter(verification_document=path, worker__user=user).exists()
    return False


def private_media(request, path):
    path = os.path.normpath(path).replace('\\', '/')
    if path.startswith('..') or path.split('/', 1)[0] not in PRIVATE_MEDIA_DIRS:
        raise Http404

    user = request.user
    allowed = (
        _signature_ok(path, request.GET.get('sig', ''))
        or (user.is_authenticated and (user.is_staff or _owns(user, path)))
    )
    if not allowed:
        return HttpResponseForbidden('You do not have access to this file.')

    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.isfile(full_path):
        raise Http404

    if settings.DEBUG:
        # No nginx in development - stream it directly.
        return FileResponse(open(full_path, 'rb'))

    response = HttpResponse()
    response['Content-Type'] = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'
    response['X-Accel-Redirect'] = f'/protected-media/{path}'
    response['Cache-Control'] = 'private, no-store'
    return response
