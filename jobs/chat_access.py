"""
Who may chat with whom.

- Everyone can chat with the admin team (support), and admins can chat with anyone.
- A worker and a client can chat only once the worker has ACCEPTED a job for
  that client (a service-request assignment or a direct booking). The chat
  stays open while the job runs and after it is completed; if the job is
  rejected or cancelled the chat closes (old messages stay readable).
- Workers never chat with other workers, clients never with other clients.
"""
from django.db.models import Q

# assignment / booking states that mean "the worker said yes"
OPEN_ASSIGNMENT = ('accepted', 'in_progress', 'completed')
OPEN_BOOKING = ('accepted', 'completed')


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_staff or getattr(user, 'user_type', '') == 'admin'))


def support_user():
    """The admin account workers and clients talk to."""
    from accounts.models import User
    return User.objects.filter(Q(is_staff=True) | Q(user_type='admin'), is_active=True).order_by('id').first()


def chat_partners(user):
    """
    {user_id: label} of the workers/clients this user may chat with because of
    an accepted job. The label names the job, newest first wins.
    """
    from .models import DirectHireRequest
    from .service_request_models import ServiceRequestAssignment

    partners = {}
    if is_admin(user):
        return partners
    utype = getattr(user, 'user_type', '')
    if utype == 'worker':
        rows = (ServiceRequestAssignment.objects
                .filter(worker__user=user, status__in=OPEN_ASSIGNMENT)
                .select_related('service_request').order_by('-assigned_at'))
        for a in rows:
            partners.setdefault(a.service_request.client_id, a.service_request.title)
        for b in (DirectHireRequest.objects.filter(worker__user=user, status__in=OPEN_BOOKING)
                  .order_by('-created_at')):
            partners.setdefault(b.client_id, b.title)
    elif utype == 'client':
        rows = (ServiceRequestAssignment.objects
                .filter(service_request__client=user, status__in=OPEN_ASSIGNMENT)
                .select_related('service_request', 'worker').order_by('-assigned_at'))
        for a in rows:
            partners.setdefault(a.worker.user_id, a.service_request.title)
        for b in (DirectHireRequest.objects.filter(client=user, status__in=OPEN_BOOKING)
                  .select_related('worker').order_by('-created_at')):
            partners.setdefault(b.worker.user_id, b.title)
    partners.pop(user.id, None)
    return partners


def can_chat(user, other):
    if not other or not other.is_active or other.pk == user.pk:
        return False
    if is_admin(user) or is_admin(other):
        return True
    return other.pk in chat_partners(user)


CLOSED_REASON = ('You can chat with a worker or client only after the worker has accepted '
                 'your job. Contact support if you need help.')
