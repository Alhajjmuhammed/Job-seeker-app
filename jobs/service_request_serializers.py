"""
Serializers for Service Request API
"""

from rest_framework import serializers
from .service_request_models import ServiceRequest, TimeTracking, WorkerActivity
from workers.models import WorkerProfile, Category
from accounts.models import User


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'icon']


class WorkerBasicSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = WorkerProfile
        fields = ['id', 'user_name', 'user_email', 'phone', 'hourly_rate', 'availability']


class ClientBasicSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone_number']


class ServiceRequestSerializer(serializers.ModelSerializer):
    """Full service request serializer"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone_number', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    worker_name = serializers.CharField(source='assigned_worker.user.get_full_name', read_only=True, allow_null=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    urgency_display = serializers.CharField(source='get_urgency_display', read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'client', 'client_name', 'client_phone', 'client_email', 'category', 'category_name',
            'title', 'description', 'location', 'city',
            'preferred_date', 'preferred_time', 'estimated_duration_hours',
            'status', 'status_display', 'urgency', 'urgency_display',
            'assigned_worker', 'worker_name', 'assigned_by', 'assigned_by_name', 'assigned_at',
            'worker_accepted', 'worker_response_at', 'worker_rejection_reason',
            'work_started_at', 'work_completed_at', 'completed_by_worker_at',
            'hourly_rate', 'total_hours_worked', 'total_amount',
            'admin_notes', 'client_notes', 'completion_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'client', 'assigned_by', 'assigned_at', 'worker_response_at',
            'work_started_at', 'work_completed_at', 'completed_by_worker_at',
            'total_hours_worked', 'total_amount', 'created_at', 'updated_at'
        ]


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for client creating service request"""
    
    class Meta:
        model = ServiceRequest
        fields = [
            'category', 'title', 'description', 'location', 'city',
            'preferred_date', 'preferred_time', 'estimated_duration_hours',
            'urgency', 'client_notes'
        ]
    
    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError("This category is not currently available.")
        return value


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone_number', read_only=True)
    worker_name = serializers.CharField(source='assigned_worker.user.get_full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'category_name', 'client_name', 'client_phone', 'worker_name',
            'location', 'city', 'status', 'status_display', 'urgency',
            'preferred_date', 'preferred_time', 'created_at', 'worker_accepted'
        ]


class AdminAssignWorkerSerializer(serializers.Serializer):
    """Serializer for admin assigning worker"""
    worker_id = serializers.IntegerField(required=True)
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_worker_id(self, value):
        try:
            worker = WorkerProfile.objects.get(id=value)
            if worker.verification_status != 'verified':
                raise serializers.ValidationError("Worker must be verified to be assigned.")
            if worker.availability == 'offline':
                raise serializers.ValidationError("Worker is currently offline.")
        except WorkerProfile.DoesNotExist:
            raise serializers.ValidationError("Worker not found.")
        return value


class WorkerResponseSerializer(serializers.Serializer):
    """Serializer for worker accepting/rejecting assignment"""
    accepted = serializers.BooleanField(required=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class TimeTrackingSerializer(serializers.ModelSerializer):
    """Serializer for time tracking"""
    worker_name = serializers.CharField(source='worker.user.get_full_name', read_only=True)
    service_title = serializers.CharField(source='service_request.title', read_only=True)
    
    class Meta:
        model = TimeTracking
        fields = [
            'id', 'service_request', 'service_title', 'worker', 'worker_name',
            'clock_in', 'clock_out', 'clock_in_location', 'clock_out_location',
            'duration_hours', 'notes', 'verified_by_client', 'verified_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['duration_hours', 'verified_by_client', 'verified_at']


class ClockInSerializer(serializers.Serializer):
    """Serializer for clocking in"""
    location = serializers.CharField(required=False, allow_blank=True)


class ClockOutSerializer(serializers.Serializer):
    """Serializer for clocking out"""
    location = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class CompleteServiceSerializer(serializers.Serializer):
    """Serializer for worker completing service"""
    completion_notes = serializers.CharField(required=False, allow_blank=True)


class WorkerActivitySerializer(serializers.ModelSerializer):
    """Serializer for worker activity log"""
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    service_title = serializers.CharField(source='service_request.title', read_only=True, allow_null=True)
    
    class Meta:
        model = WorkerActivity
        fields = [
            'id', 'activity_type', 'activity_type_display', 'description',
            'service_request', 'service_title', 'location', 'duration',
            'amount_earned', 'created_at'
        ]


class WorkerStatsSerializer(serializers.Serializer):
    """Serializer for worker statistics"""
    total_services = serializers.IntegerField()
    completed_services = serializers.IntegerField()
    in_progress_services = serializers.IntegerField()
    total_hours_worked = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_earned = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2, allow_null=True)
    this_week_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    this_week_earned = serializers.DecimalField(max_digits=10, decimal_places=2)


class ClientStatsSerializer(serializers.Serializer):
    """Serializer for client statistics"""
    total_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    in_progress_requests = serializers.IntegerField()
    completed_requests = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2)
