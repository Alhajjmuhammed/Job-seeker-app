"""
Worker availability calendar and scheduling for Worker Connect.

Allows workers to set their availability and clients to see when workers are free.
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional


class DayOfWeek:
    """Day of week constants."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
    
    CHOICES = [
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
        (SUNDAY, 'Sunday'),
    ]


class RecurringAvailability(models.Model):
    """
    Recurring weekly availability for workers.
    e.g., "Available Mondays 9AM-5PM"
    """
    
    worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.CASCADE,
        related_name='recurring_availability'
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['worker', 'day_of_week', 'start_time']
        indexes = [
            models.Index(fields=['worker', 'is_active']),
            models.Index(fields=['day_of_week']),
        ]
    
    def __str__(self):
        day_name = dict(DayOfWeek.CHOICES).get(self.day_of_week)
        return f"{self.worker} - {day_name} {self.start_time}-{self.end_time}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time')


class AvailabilityException(models.Model):
    """
    One-time availability exceptions (time off, special availability).
    Overrides recurring availability for specific dates.
    """
    
    EXCEPTION_TYPE_CHOICES = [
        ('unavailable', 'Unavailable'),
        ('available', 'Available'),
    ]
    
    worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.CASCADE,
        related_name='availability_exceptions'
    )
    date = models.DateField()
    exception_type = models.CharField(max_length=20, choices=EXCEPTION_TYPE_CHOICES)
    start_time = models.TimeField(null=True, blank=True)  # Null = all day
    end_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['worker', 'date']),
        ]
    
    def __str__(self):
        return f"{self.worker} - {self.date} ({self.exception_type})"
    
    @property
    def is_all_day(self):
        return self.start_time is None


class BookedSlot(models.Model):
    """
    Booked time slots for jobs.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    worker = models.ForeignKey(
        'workers.WorkerProfile',
        on_delete=models.CASCADE,
        related_name='booked_slots'
    )
    job = models.ForeignKey(
        'jobs.JobRequest',
        on_delete=models.CASCADE,
        related_name='booked_slots',
        null=True,
        blank=True
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['worker', 'date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.worker} - {self.date} {self.start_time}-{self.end_time}"


class AvailabilityService:
    """
    Service for managing worker availability.
    """
    
    @staticmethod
    def get_worker_availability(
        worker_profile,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> List[Dict[str, Any]]:
        """
        Get worker's availability for a date range.
        
        Returns list of available slots combining recurring availability,
        exceptions, and existing bookings.
        """
        availability = []
        current_date = start_date
        
        while current_date <= end_date:
            day_slots = AvailabilityService._get_day_availability(
                worker_profile, current_date
            )
            availability.append({
                'date': current_date.isoformat(),
                'day_of_week': current_date.weekday(),
                'day_name': current_date.strftime('%A'),
                'slots': day_slots,
                'is_available': len(day_slots) > 0,
            })
            current_date += timedelta(days=1)
        
        return availability
    
    @staticmethod
    def _get_day_availability(worker_profile, date: datetime.date) -> List[Dict[str, Any]]:
        """Get available slots for a specific day."""
        slots = []
        day_of_week = date.weekday()
        
        # Check for all-day exception
        all_day_exception = AvailabilityException.objects.filter(
            worker=worker_profile,
            date=date,
            start_time__isnull=True
        ).first()
        
        if all_day_exception:
            if all_day_exception.exception_type == 'unavailable':
                return []  # Worker is unavailable all day
            # If 'available', continue to check specific times
        
        # Get recurring availability for this day
        recurring = RecurringAvailability.objects.filter(
            worker=worker_profile,
            day_of_week=day_of_week,
            is_active=True
        )
        
        # Get time-specific exceptions
        exceptions = AvailabilityException.objects.filter(
            worker=worker_profile,
            date=date,
            start_time__isnull=False
        )
        
        # Get booked slots
        bookings = BookedSlot.objects.filter(
            worker=worker_profile,
            date=date,
            status__in=['pending', 'confirmed']
        )
        
        # Build available slots from recurring
        for rec in recurring:
            slot = {
                'start_time': rec.start_time.strftime('%H:%M'),
                'end_time': rec.end_time.strftime('%H:%M'),
                'is_available': True,
                'source': 'recurring',
            }
            
            # Check if overridden by exception
            for exc in exceptions:
                if AvailabilityService._times_overlap(
                    rec.start_time, rec.end_time,
                    exc.start_time, exc.end_time
                ):
                    if exc.exception_type == 'unavailable':
                        slot['is_available'] = False
                        slot['reason'] = exc.reason
            
            # Check if already booked
            for booking in bookings:
                if AvailabilityService._times_overlap(
                    rec.start_time, rec.end_time,
                    booking.start_time, booking.end_time
                ):
                    slot['is_available'] = False
                    slot['reason'] = 'Already booked'
                    slot['booking_id'] = booking.id
            
            slots.append(slot)
        
        # Add any special available times from exceptions
        for exc in exceptions:
            if exc.exception_type == 'available':
                slots.append({
                    'start_time': exc.start_time.strftime('%H:%M'),
                    'end_time': exc.end_time.strftime('%H:%M'),
                    'is_available': True,
                    'source': 'exception',
                })
        
        return slots
    
    @staticmethod
    def _times_overlap(start1, end1, start2, end2) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1
    
    @staticmethod
    def check_availability(
        worker_profile,
        date: datetime.date,
        start_time: time,
        end_time: time
    ) -> Dict[str, Any]:
        """
        Check if a worker is available for a specific time slot.
        
        Returns availability status and any conflicts.
        """
        # Check all-day exception
        all_day_unavailable = AvailabilityException.objects.filter(
            worker=worker_profile,
            date=date,
            exception_type='unavailable',
            start_time__isnull=True
        ).exists()
        
        if all_day_unavailable:
            return {'available': False, 'reason': 'Worker unavailable on this date'}
        
        # Check if within recurring availability
        day_of_week = date.weekday()
        has_recurring = RecurringAvailability.objects.filter(
            worker=worker_profile,
            day_of_week=day_of_week,
            is_active=True,
            start_time__lte=start_time,
            end_time__gte=end_time
        ).exists()
        
        # Check for special available exception
        has_exception_available = AvailabilityException.objects.filter(
            worker=worker_profile,
            date=date,
            exception_type='available',
            start_time__lte=start_time,
            end_time__gte=end_time
        ).exists()
        
        if not has_recurring and not has_exception_available:
            return {'available': False, 'reason': 'Outside worker\'s available hours'}
        
        # Check for time-specific unavailable exception
        has_exception_unavailable = AvailabilityException.objects.filter(
            worker=worker_profile,
            date=date,
            exception_type='unavailable'
        ).exclude(start_time__isnull=True).exists()
        
        if has_exception_unavailable:
            # Check overlap
            exceptions = AvailabilityException.objects.filter(
                worker=worker_profile,
                date=date,
                exception_type='unavailable'
            ).exclude(start_time__isnull=True)
            
            for exc in exceptions:
                if AvailabilityService._times_overlap(start_time, end_time, exc.start_time, exc.end_time):
                    return {'available': False, 'reason': exc.reason or 'Worker unavailable'}
        
        # Check existing bookings
        conflicting_booking = BookedSlot.objects.filter(
            worker=worker_profile,
            date=date,
            status__in=['pending', 'confirmed']
        ).first()
        
        if conflicting_booking:
            if AvailabilityService._times_overlap(
                start_time, end_time,
                conflicting_booking.start_time, conflicting_booking.end_time
            ):
                return {
                    'available': False,
                    'reason': 'Time slot already booked',
                    'conflict_id': conflicting_booking.id
                }
        
        return {'available': True}
    
    @staticmethod
    def book_slot(
        worker_profile,
        job,
        date: datetime.date,
        start_time: time,
        end_time: time,
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        Book a time slot for a job.
        """
        # Check availability first
        check = AvailabilityService.check_availability(
            worker_profile, date, start_time, end_time
        )
        
        if not check['available']:
            return {'success': False, 'error': check['reason']}
        
        # Create booking
        booking = BookedSlot.objects.create(
            worker=worker_profile,
            job=job,
            date=date,
            start_time=start_time,
            end_time=end_time,
            status='pending',
            notes=notes
        )
        
        return {
            'success': True,
            'booking_id': booking.id,
            'message': 'Slot booked successfully'
        }
    
    @staticmethod
    def set_recurring_availability(
        worker_profile,
        schedules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Set recurring weekly availability for a worker.
        
        Args:
            schedules: List of dicts with day_of_week, start_time, end_time
            
        Example:
            [
                {'day_of_week': 0, 'start_time': '09:00', 'end_time': '17:00'},
                {'day_of_week': 1, 'start_time': '09:00', 'end_time': '17:00'},
            ]
        """
        # Deactivate existing
        RecurringAvailability.objects.filter(worker=worker_profile).update(is_active=False)
        
        created = []
        for schedule in schedules:
            start = datetime.strptime(schedule['start_time'], '%H:%M').time()
            end = datetime.strptime(schedule['end_time'], '%H:%M').time()
            
            obj, _ = RecurringAvailability.objects.update_or_create(
                worker=worker_profile,
                day_of_week=schedule['day_of_week'],
                start_time=start,
                defaults={
                    'end_time': end,
                    'is_active': True
                }
            )
            created.append(obj.id)
        
        return {
            'success': True,
            'created_count': len(created),
            'message': 'Availability updated'
        }
