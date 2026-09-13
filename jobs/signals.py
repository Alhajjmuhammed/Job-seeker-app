"""
Keep a service request honest when its assignments disappear.

Deleting a worker cascades their ServiceRequestAssignment rows away, but
nothing looked at the request afterwards. A job whose only worker was
deleted stayed 'in_progress' with nobody on it: the client saw work
underway that no one was doing, and it never came back to the admin queue
because the queue lists pending requests.

Hooking the assignment's deletion rather than the delete endpoints means it
holds however the row goes - a bulk action, the Django admin, or a cascade
from removing the account.
"""
from django.db.models.signals import post_delete
from django.dispatch import receiver

from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment

# A request that has reached one of these is finished with; losing an
# assignment afterwards should not drag it back into the queue.
SETTLED = ('completed', 'cancelled')


@receiver(post_delete, sender=ServiceRequestAssignment,
          dispatch_uid='requeue_request_when_assignment_deleted')
def requeue_request_when_assignment_deleted(sender, instance, **kwargs):
    request_id = instance.service_request_id
    if not request_id:
        return

    service_request = ServiceRequest.objects.filter(pk=request_id).first()
    if service_request is None or service_request.status in SETTLED:
        return

    still_live = ServiceRequestAssignment.objects.filter(
        service_request_id=request_id
    ).exclude(status__in=ServiceRequest.DEAD_ASSIGNMENT_STATUSES).exists()
    if still_live:
        return

    if service_request.status != 'pending':
        service_request.status = 'pending'
        service_request.save(update_fields=['status', 'updated_at'])
