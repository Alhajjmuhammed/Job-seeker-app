"""
URL routes for worker availability API.
"""

from django.urls import path
from . import availability_views

urlpatterns = [
    # Availability calendar
    path('availability/', availability_views.get_availability, name='get_availability'),
    path('availability/<int:worker_id>/', availability_views.get_availability, name='get_worker_availability'),
    
    # Recurring schedules
    path('availability/recurring/', availability_views.get_recurring_availability, name='get_recurring'),
    path('availability/recurring/set/', availability_views.set_recurring_availability, name='set_recurring'),
    
    # Exceptions
    path('availability/exceptions/', availability_views.get_exceptions, name='get_exceptions'),
    path('availability/exceptions/add/', availability_views.add_exception, name='add_exception'),
    path('availability/exceptions/<int:exception_id>/', availability_views.delete_exception, name='delete_exception'),
    
    # Slot checking and booking
    path('availability/check/', availability_views.check_slot, name='check_slot'),
    path('availability/slots/', availability_views.get_booked_slots, name='get_slots'),
    path('availability/slots/<int:slot_id>/', availability_views.update_slot_status, name='update_slot'),
]
