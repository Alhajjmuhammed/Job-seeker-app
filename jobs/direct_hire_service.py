"""
Direct hire (a client books one worker straight away) - the business rules in
ONE place. The website views (jobs/views.py) and the app API
(jobs/direct_hire_api.py, jobs/api_views.py) both call these functions, so the
two can never drift apart.

Every function raises DirectHireError(message, code) when the action is not
allowed; the message is a sentence a person can read.
"""
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from .models import DirectHireRequest

# the booking states in which the two sides may see each other's phone / the address
OPEN_STATES = ('accepted', 'completed')


class DirectHireError(Exception):
    def __init__(self, message, code='invalid', status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def _notify(hire):
    from worker_connect.notification_service import NotificationService
    NotificationService.notify_direct_hire(hire)


def is_worker_of(hire, user):
    return bool(user and user.is_authenticated and hire.worker.user_id == user.pk)


def is_party(hire, user):
    return bool(user and user.is_authenticated and (hire.client_id == user.pk or is_worker_of(hire, user)))


# ---------------------------------------------------------------- create
def suggested_rate(worker):
    """A sensible opening offer: what the platform charges for one worker in
    this worker's own category (work is priced per request, not per hour)."""
    category = worker.categories.first()
    return category.daily_rate if category else None


def check_can_book(client, worker):
    if not getattr(client, 'is_client', False):
        raise DirectHireError('Only clients can request workers.', 'not_client', 403)
    if not worker.can_accept_direct_hires:
        raise DirectHireError('This worker is not available for direct hire requests. '
                              'They need to upload ID and be verified.', 'worker_not_eligible')


def create(client, worker, form):
    """Save a valid DirectHireRequestForm as a booking from `client` to `worker`
    and tell the worker. The form does the field checks (duration >= 1,
    rate > 0, start not in the past)."""
    check_can_book(client, worker)
    hire = form.save(commit=False)
    hire.client = client
    hire.worker = worker
    hire.save()
    _notify(hire)
    return hire


# ---------------------------------------------------------------- worker answers
def accept_problem(hire, user):
    """Why `user` can't accept this booking now, or None if they can."""
    if not is_worker_of(hire, user):
        return DirectHireError('Access denied.', 'forbidden', 403)
    if hire.status != 'pending':
        return DirectHireError('This request has already been responded to.', 'already_responded')
    if hire.worker.availability == 'busy':  # busy with other work: decline, or finish first
        return DirectHireError('You are busy with other work. Finish it first, or decline this request.',
                               'worker_busy')
    return None


def reject_problem(hire, user):
    if not is_worker_of(hire, user):
        return DirectHireError('Access denied.', 'forbidden', 403)
    if hire.status != 'pending':
        return DirectHireError('This request has already been responded to.', 'already_responded')
    return None


def accept(hire, user, message=''):
    with transaction.atomic():
        locked = DirectHireRequest.objects.select_for_update().select_related('worker').get(pk=hire.pk)
        problem = accept_problem(locked, user)
        if problem:
            raise problem
        locked.status = 'accepted'
        locked.worker_response_message = (message or '')[:1000]
        locked.responded_at = timezone.now()
        locked.save()
        worker = locked.worker
        worker.availability = 'busy'
        worker.save(update_fields=['availability'])
    hire.refresh_from_db()
    _notify(hire)
    return hire


def reject(hire, user, reason=''):
    with transaction.atomic():
        locked = DirectHireRequest.objects.select_for_update().select_related('worker').get(pk=hire.pk)
        problem = reject_problem(locked, user)
        if problem:
            raise problem
        locked.status = 'rejected'
        locked.worker_response_message = (reason or '')[:1000]
        locked.responded_at = timezone.now()
        locked.save()
    hire.refresh_from_db()
    _notify(hire)
    return hire


# ---------------------------------------------------------------- client finishes
def complete_problem(hire, user):
    if not (user and user.is_authenticated and hire.client_id == user.pk):
        return DirectHireError('Access denied.', 'forbidden', 403)
    if hire.status != 'accepted':
        return DirectHireError('Can only complete accepted requests.', 'not_accepted')
    return None


def parse_rating(value):
    """1-5 or None (blank / 'abc' / 9 are 'no rating', never a crash)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 5 else None


def complete(hire, user, rating=None, feedback=''):
    """The client marks the work done (and may rate the worker 1-5)."""
    from clients.models import Rating
    rating_value = parse_rating(rating)
    feedback = (feedback or '').strip()
    with transaction.atomic():
        locked = DirectHireRequest.objects.select_for_update().select_related('worker').get(pk=hire.pk)
        problem = complete_problem(locked, user)
        if problem:
            if problem.code == 'not_accepted' and hire.status == 'accepted':
                problem = DirectHireError('This booking is no longer active.', 'not_accepted')
            raise problem
        locked.status = 'completed'
        locked.completed_at = timezone.now()
        locked.client_rating = rating_value
        locked.client_feedback = feedback
        locked.save()

        worker = locked.worker
        worker.completed_jobs += 1
        worker.total_jobs += 1
        worker.total_earnings += locked.total_amount
        # a real Rating row, so it counts toward the worker's average and review list
        if rating_value:
            Rating.objects.update_or_create(client=user, worker=worker,
                                            defaults={'rating': rating_value, 'review': feedback})
        ratings = Rating.objects.filter(worker=worker)
        if ratings.exists():
            worker.average_rating = round(ratings.aggregate(Avg('rating'))['rating__avg'], 2)
            worker.total_reviews = ratings.count()
        worker.save()
    # free the worker only if nothing else keeps them busy
    locked.free_worker_if_idle()
    hire.refresh_from_db()
    return hire


# ---------------------------------------------------------------- cancel
def cancel(hire, user, reason=''):
    if not is_party(hire, user):
        raise DirectHireError('Access denied.', 'forbidden', 403)
    if not hire.cancel(user, (reason or '').strip()[:500]):
        raise DirectHireError('This booking can no longer be cancelled.', 'cannot_cancel')
    return hire


# ---------------------------------------------------------------- lists
def for_user(user, role=None):
    """The bookings this user is part of: as the client, or as the worker."""
    qs = DirectHireRequest.objects.select_related('worker__user', 'client')
    if role is None:
        role = 'worker' if getattr(user, 'user_type', '') == 'worker' else 'client'
    if role == 'worker':
        return qs.filter(worker__user=user)
    return qs.filter(client=user)


def filter_status(qs, status):
    """?status=pending | accepted | rejected,cancelled | all ('' = all)."""
    wanted = [s.strip() for s in (status or '').split(',') if s.strip() and s.strip() != 'all']
    valid = {k for k, _ in DirectHireRequest.STATUS_CHOICES}
    wanted = [s for s in wanted if s in valid]
    return qs.filter(status__in=wanted) if wanted else qs
