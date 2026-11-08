"""
Applies the client's chosen assignment_mode right after a ServiceRequest is
created. Shared by all three client creation entry points (API, serializer,
web) so the auto-assign logic isn't duplicated three times.
"""

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
from workers.models import WorkerProfile
from workers.cities import city_key
from workers.proximity import rank_by_distance


def bookable_workers(category):
    """
    Workers a client may be matched with in this category: verified, shown
    publicly, and with an active account. The same rule for the list a
    client browses, the worker a client picks, and the nearest-worker match.
    """
    return WorkerProfile.objects.filter(
        categories=category,
        verification_status='verified',
        is_public=True,
        user__is_active=True,
    ).distinct()


def validate_preferred_worker(worker, category):
    """Error message if a client may not request this worker, else None."""
    if not bookable_workers(category).filter(pk=worker.pk).exists():
        if not worker.categories.filter(pk=getattr(category, 'pk', category)).exists():
            return "The requested worker doesn't offer this category."
        return "The requested worker is not available for booking."
    return None


def apply_assignment_mode(service_request):
    """
    mode == 'admin_choice' (default) or 'client_choice': no-op here.
    client_choice's preferred_worker is already set at creation time; the
    admin's existing "Client Requested a Worker" banner reacts to it.

    mode == 'auto_nearest': assign the nearest available, verified,
    category-matching worker(s), using the same
    admin_panel.service_request_views._create_assignment helper the admin's
    "auto-assign nearest" button uses - assigned_by=None marks it as
    system-assigned rather than a human admin's call.

    Nearest is by GPS when the request and workers have coordinates. Workers
    without a saved location are then matched by the request's city, best
    rated first, so the mode still works while locations are collected (no
    worker had one, so it never assigned anyone). If nobody matches, the
    request falls back to a normal admin_choice request - this never blocks
    or fails request creation.
    """
    if service_request.assignment_mode != 'auto_nearest':
        return

    # Never dispatch workers to a request that is already closed - verifying
    # a late payment on a cancelled request used to send workers out.
    if service_request.status in ('cancelled', 'completed'):
        return

    # Workers are only sent once the booking is paid. This used to assign
    # immediately, so an unpaid request still got workers dispatched.
    # mark_payment_verified() calls back in here once payment is confirmed.
    if not service_request.is_paid:
        return

    # Account for assignments that may already exist - this can be called
    # more than once on the same request (e.g. the client updates a still-
    # pending request and re-triggers auto_nearest), and without this check
    # it would try to fill workers_needed all over again on top of whatever
    # was already assigned, over-assigning the request.
    existing_assignments = ServiceRequestAssignment.objects.filter(service_request=service_request)
    # rejected/cancelled rows do not occupy a slot
    existing_count = existing_assignments.exclude(
        status__in=ServiceRequest.DEAD_ASSIGNMENT_STATUSES).count()
    slots_remaining = service_request.workers_needed - existing_count
    if slots_remaining <= 0:
        return

    already_assigned_ids = set(existing_assignments.values_list('worker_id', flat=True))

    candidates = bookable_workers(service_request.category).filter(
        availability='available',
    ).exclude(id__in=already_assigned_ids) if service_request.category else WorkerProfile.objects.none()

    chosen = []  # (worker, how it was matched)
    if service_request.latitude is not None and service_request.longitude is not None:
        for worker in rank_by_distance(candidates, service_request.latitude,
                                       service_request.longitude, limit=slots_remaining):
            chosen.append((worker, f'nearest, {worker.distance_km:.1f} km'))

    city = (service_request.city or '').strip()
    wanted = city_key(city)
    if len(chosen) < slots_remaining and wanted:
        # matched on a normalised key: workers type "ZANZIBAR", "Zanzibra",
        # "Stone Town" or their neighbourhood for the same place
        taken = {w.id for w, _ in chosen}
        same_city = [w for w in candidates.exclude(id__in=taken).order_by('-average_rating', '-completed_jobs')
                     if city_key(w.city) == wanted]
        for worker in same_city[:slots_remaining - len(chosen)]:
            chosen.append((worker, f'same city, {city}'))

    if not chosen:
        if existing_count == 0:
            service_request.assignment_mode = 'admin_choice'
            service_request.save(update_fields=['assignment_mode'])
        return

    from admin_panel.service_request_views import _create_assignment

    for idx, (worker, how) in enumerate(chosen, start=existing_count + 1):
        _create_assignment(
            service_request, worker, admin_user=None,
            assignment_number=idx,
            activity_description=f'Auto-assigned ({how}) to: {service_request.title}'
        )

    total_assignments = existing_count + len(chosen)
    if total_assignments >= service_request.workers_needed and service_request.status == 'pending':
        service_request.status = 'assigned'
        service_request.save(update_fields=['status'])
