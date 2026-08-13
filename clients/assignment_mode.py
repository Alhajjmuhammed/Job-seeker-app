"""
Applies the client's chosen assignment_mode right after a ServiceRequest is
created. Shared by all three client creation entry points (API, serializer,
web) so the auto-assign logic isn't duplicated three times.
"""

from jobs.service_request_models import ServiceRequestAssignment
from workers.models import WorkerProfile
from workers.proximity import rank_by_distance


def apply_assignment_mode(service_request):
    """
    mode == 'admin_choice' (default) or 'client_choice': no-op here.
    client_choice's preferred_worker is already set at creation time; the
    admin's existing "Client Requested a Worker" banner reacts to it.

    mode == 'auto_nearest': try to assign the nearest available, verified,
    category-matching worker(s) immediately, using the same
    admin_panel.service_request_views._create_assignment helper the admin's
    "auto-assign nearest" button uses - assigned_by=None marks it as
    system-assigned rather than a human admin's call. Falls back to leaving
    the request as a normal pending admin_choice request if there are no
    coordinates or no matching workers - this never blocks or fails request
    creation.
    """
    if service_request.assignment_mode != 'auto_nearest':
        return

    # Account for assignments that may already exist - this can be called
    # more than once on the same request (e.g. the client updates a still-
    # pending request and re-triggers auto_nearest), and without this check
    # it would try to fill workers_needed all over again on top of whatever
    # was already assigned, over-assigning the request.
    existing_assignments = ServiceRequestAssignment.objects.filter(service_request=service_request)
    existing_count = existing_assignments.count()
    slots_remaining = service_request.workers_needed - existing_count
    if slots_remaining <= 0:
        return

    if service_request.latitude is None or service_request.longitude is None:
        if existing_count == 0:
            service_request.assignment_mode = 'admin_choice'
            service_request.save(update_fields=['assignment_mode'])
        return

    already_assigned_ids = set(existing_assignments.values_list('worker_id', flat=True))

    candidates = WorkerProfile.objects.filter(
        verification_status='verified',
        availability='available'
    ).exclude(id__in=already_assigned_ids)
    if service_request.category:
        candidates = candidates.filter(categories=service_request.category)

    nearest = rank_by_distance(
        list(candidates), service_request.latitude, service_request.longitude,
        limit=slots_remaining
    )

    if not nearest:
        if existing_count == 0:
            service_request.assignment_mode = 'admin_choice'
            service_request.save(update_fields=['assignment_mode'])
        return

    from admin_panel.service_request_views import _create_assignment

    for idx, worker in enumerate(nearest, start=existing_count + 1):
        _create_assignment(
            service_request, worker, admin_user=None,
            assignment_number=idx,
            activity_description=f'Auto-assigned (nearest, {worker.distance_km:.1f} km) to: {service_request.title}'
        )

    total_assignments = existing_count + len(nearest)
    if total_assignments >= service_request.workers_needed:
        service_request.status = 'assigned'
        service_request.save(update_fields=['status'])
