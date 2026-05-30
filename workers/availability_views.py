"""
Availability API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta

from workers.models import WorkerProfile
from .availability import (
    AvailabilityService,
    RecurringAvailability,
    AvailabilityException,
    BookedSlot,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_availability(request, worker_id=None):
    """
    Get worker availability for a date range.
    
    Query params:
        - start_date: Start date (YYYY-MM-DD), defaults to today
        - end_date: End date (YYYY-MM-DD), defaults to 7 days from start
        - worker_id: Worker ID (optional, defaults to current user's profile)
    """
    try:
        # Get worker profile
        if worker_id:
            worker_profile = get_object_or_404(WorkerProfile, id=worker_id)
        else:
            worker_profile = get_object_or_404(WorkerProfile, user=request.user)
        
        # Parse dates
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = datetime.now().date()
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = start_date + timedelta(days=7)
        
        # Get availability
        availability = AvailabilityService.get_worker_availability(
            worker_profile, start_date, end_date
        )
        
        return Response({
            'worker_id': worker_profile.id,
            'worker_name': worker_profile.user.get_full_name() or worker_profile.user.username,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'availability': availability,
        })
    
    except ValueError as e:
        return Response({
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_recurring_availability(request):
    """
    Set recurring weekly availability for the authenticated worker.
    
    Request body:
        {
            "schedules": [
                {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"},
                {"day_of_week": 1, "start_time": "09:00", "end_time": "17:00"},
                ...
            ]
        }
    """
    worker_profile = get_object_or_404(WorkerProfile, user=request.user)
    
    schedules = request.data.get('schedules', [])
    
    if not schedules:
        return Response({
            'error': 'No schedules provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate schedules
    for schedule in schedules:
        if 'day_of_week' not in schedule:
            return Response({
                'error': 'day_of_week is required for each schedule'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if schedule['day_of_week'] not in range(7):
            return Response({
                'error': 'day_of_week must be 0-6 (Monday-Sunday)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if 'start_time' not in schedule or 'end_time' not in schedule:
            return Response({
                'error': 'start_time and end_time are required'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    result = AvailabilityService.set_recurring_availability(
        worker_profile, schedules
    )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recurring_availability(request):
    """Get worker's recurring availability schedule."""
    worker_profile = get_object_or_404(WorkerProfile, user=request.user)
    
    recurring = RecurringAvailability.objects.filter(
        worker=worker_profile,
        is_active=True
    )
    
    schedules = []
    for rec in recurring:
        schedules.append({
            'id': rec.id,
            'day_of_week': rec.day_of_week,
            'day_name': rec.get_day_of_week_display(),
            'start_time': rec.start_time.strftime('%H:%M'),
            'end_time': rec.end_time.strftime('%H:%M'),
        })
    
    return Response({'schedules': schedules})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_exception(request):
    """
    Add an availability exception (time off or special availability).
    
    Request body:
        {
            "date": "2024-12-25",
            "exception_type": "unavailable",
            "start_time": "09:00",  // Optional, null = all day
            "end_time": "17:00",    // Optional
            "reason": "Holiday"      // Optional
        }
    """
    worker_profile = get_object_or_404(WorkerProfile, user=request.user)
    
    date_str = request.data.get('date')
    exception_type = request.data.get('exception_type')
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    reason = request.data.get('reason', '')
    
    if not date_str:
        return Response({
            'error': 'date is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if exception_type not in ['available', 'unavailable']:
        return Response({
            'error': 'exception_type must be "available" or "unavailable"'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Parse times if provided
    start_time_obj = None
    end_time_obj = None
    if start_time:
        start_time_obj = datetime.strptime(start_time, '%H:%M').time()
    if end_time:
        end_time_obj = datetime.strptime(end_time, '%H:%M').time()
    
    exception = AvailabilityException.objects.create(
        worker=worker_profile,
        date=date,
        exception_type=exception_type,
        start_time=start_time_obj,
        end_time=end_time_obj,
        reason=reason
    )
    
    return Response({
        'id': exception.id,
        'message': 'Exception added successfully'
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_exception(request, exception_id):
    """Delete an availability exception."""
    worker_profile = get_object_or_404(WorkerProfile, user=request.user)
    
    exception = get_object_or_404(
        AvailabilityException,
        id=exception_id,
        worker=worker_profile
    )
    
    exception.delete()
    
    return Response({
        'message': 'Exception deleted successfully'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_exceptions(request):
    """Get all exceptions for the authenticated worker."""
    worker_profile = get_object_or_404(WorkerProfile, user=request.user)
    
    # Default to showing future exceptions only
    start_date_str = request.query_params.get('start_date')
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = datetime.now().date()
    
    exceptions = AvailabilityException.objects.filter(
        worker=worker_profile,
        date__gte=start_date
    ).order_by('date')
    
    data = []
    for exc in exceptions:
        data.append({
            'id': exc.id,
            'date': exc.date.isoformat(),
            'exception_type': exc.exception_type,
            'start_time': exc.start_time.strftime('%H:%M') if exc.start_time else None,
            'end_time': exc.end_time.strftime('%H:%M') if exc.end_time else None,
            'reason': exc.reason,
            'is_all_day': exc.is_all_day,
        })
    
    return Response({'exceptions': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_slot(request):
    """
    Check if a time slot is available.
    
    Request body:
        {
            "worker_id": 1,
            "date": "2024-01-15",
            "start_time": "09:00",
            "end_time": "12:00"
        }
    """
    worker_id = request.data.get('worker_id')
    date_str = request.data.get('date')
    start_time_str = request.data.get('start_time')
    end_time_str = request.data.get('end_time')
    
    if not all([worker_id, date_str, start_time_str, end_time_str]):
        return Response({
            'error': 'worker_id, date, start_time, and end_time are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        worker_profile = get_object_or_404(WorkerProfile, id=worker_id)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        return Response({
            'error': 'Invalid date or time format'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = AvailabilityService.check_availability(
        worker_profile, date, start_time, end_time
    )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_booked_slots(request):
    """Get booked slots for the authenticated worker."""
    worker_profile = get_object_or_404(WorkerProfile, user=request.user)
    
    # Parse date filter
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    status_filter = request.query_params.get('status')
    
    slots = BookedSlot.objects.filter(worker=worker_profile)
    
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        slots = slots.filter(date__gte=start_date)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        slots = slots.filter(date__lte=end_date)
    
    if status_filter:
        slots = slots.filter(status=status_filter)
    
    data = []
    for slot in slots:
        data.append({
            'id': slot.id,
            'date': slot.date.isoformat(),
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M'),
            'status': slot.status,
            'job_id': slot.job_id,
            'notes': slot.notes,
        })
    
    return Response({'slots': data})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_slot_status(request, slot_id):
    """
    Update a booked slot's status.
    
    Request body:
        {
            "status": "confirmed"
        }
    """
    worker_profile = get_object_or_404(WorkerProfile, user=request.user)
    
    slot = get_object_or_404(
        BookedSlot,
        id=slot_id,
        worker=worker_profile
    )
    
    new_status = request.data.get('status')
    if new_status not in ['pending', 'confirmed', 'cancelled', 'completed']:
        return Response({
            'error': 'Invalid status'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    slot.status = new_status
    slot.save()
    
    return Response({
        'id': slot.id,
        'status': slot.status,
        'message': 'Status updated successfully'
    })
