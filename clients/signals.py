"""
Keep a client's stored totals in step with their service requests.

A booking can be created in four different places, and the totals were kept
by a += in only one of them, so they were wrong for every client who booked
any other way. Hooking the request itself means it no longer matters which
view created it - and because payment_status can change long after the
booking, this has to run on every save, not just creation.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from jobs.service_request_models import ServiceRequest


@receiver(post_save, sender=ServiceRequest, dispatch_uid='client_totals_save')
@receiver(post_delete, sender=ServiceRequest, dispatch_uid='client_totals_delete')
def update_client_totals(sender, instance, **kwargs):
    profile = getattr(instance.client, 'client_profile', None)
    if profile is not None:
        profile.recalculate_totals()
