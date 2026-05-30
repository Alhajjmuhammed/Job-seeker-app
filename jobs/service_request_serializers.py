"""
Serializers for Service Request API
"""

from rest_framework import serializers
from .service_request_models import ServiceRequest, TimeTracking, WorkerActivity, ServiceRequestAssignment
from workers.models import WorkerProfile, Category
from accounts.models import User


class AssignmentWorkerSerializer(serializers.ModelSerializer):
    """Nested serializer for worker info in assignments"""
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    rating = serializers.DecimalField(source='average_rating', max_digits=3, decimal_places=2, read_only=True, allow_null=True)
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkerProfile
        fields = ['id', 'full_name', 'phone_number', 'email', 'rating', 'profile_picture']
    
    def get_profile_picture(self, obj):
        """Return full URL for profile image or None"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
        return None


class AssignmentBasicSerializer(serializers.ModelSerializer):
    """Simplified assignment serializer for nesting in service request (client view - no payment info)"""
    worker = AssignmentWorkerSerializer(read_only=True)
    
    class Meta:
        model = ServiceRequestAssignment
        fields = [
            'id', 'assignment_number', 'status', 'worker',
            'worker_response_at', 'worker_rejection_reason', 'assigned_at'
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'icon']


class WorkerBasicSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    rating = serializers.DecimalField(source='average_rating', max_digits=3, decimal_places=2, read_only=True)
    
    class Meta:
        model = WorkerProfile
        fields = ['id', 'full_name', 'email', 'phone_number', 'profile_image', 'rating', 'availability']


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
    duration_type_display = serializers.CharField(source='get_duration_type_display', read_only=True)
    assigned_worker = WorkerBasicSerializer(read_only=True)
    assignments = serializers.SerializerMethodField()  # Filter out rejected for clients
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'client', 'client_name', 'client_phone', 'client_email', 'category', 'category_name',
            'title', 'description', 'location', 'city',
            'preferred_date', 'preferred_time',
            # NEW: Duration & Pricing fields
            'duration_type', 'duration_type_display', 'duration_days',
            'service_start_date', 'service_end_date',
            'workers_needed',  # NEW: Multiple workers support
            'assignments',  # NEW: List of worker assignments (filtered)
            'daily_rate', 'total_price',
            'payment_status', 'payment_method', 'paid_at', 'payment_transaction_id',
            'payment_screenshot', 'payment_verified', 'payment_verified_by', 'payment_verified_at',
            # Legacy field
            'estimated_duration_hours',
            'status', 'status_display', 'urgency', 'urgency_display',
            'assigned_worker', 'worker_name', 'assigned_by', 'assigned_by_name', 'assigned_at',
            'worker_accepted', 'worker_response_at', 'worker_rejection_reason',
            'work_started_at', 'work_completed_at', 'completed_by_worker_at',
            'hourly_rate', 'total_hours_worked', 'total_amount',
            'admin_notes', 'client_notes', 'completion_notes',
            'client_rating', 'client_review',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'client', 'assigned_by', 'assigned_at', 'worker_response_at',
            'work_started_at', 'work_completed_at', 'completed_by_worker_at',
            'total_hours_worked', 'total_amount', 'created_at', 'updated_at',
            'daily_rate', 'total_price', 'duration_days', 'paid_at'
        ]
    
    def get_assignments(self, obj):
        """Filter assignments for clients - only show accepted/in_progress/completed workers"""
        # Clients only see workers who accepted (not pending or rejected)
        assignments = obj.assignments.filter(
            status__in=['accepted', 'in_progress', 'completed']
        ).order_by('assignment_number')
        return AssignmentBasicSerializer(assignments, many=True, context=self.context).data



class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for client creating service request WITH PRICING"""
    
    class Meta:
        model = ServiceRequest
        fields = [
            'category', 'title', 'description', 'location', 'city',
            'preferred_date', 'preferred_time',
            # NEW: Duration fields
            'workers_needed',  # NEW: Multiple workers support
            'urgency', 'client_notes'
        ]
    
    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError("This category is not currently available.")
        return value
    
    def validate_workers_needed(self, value):
        """Validate workers_needed is between 1 and 100"""
        if value < 1:
            raise serializers.ValidationError("At least 1 worker is required.")
        if value > 100:
            raise serializers.ValidationError("Cannot request more than 100 workers.")
        return value
    
    def validate(self, data):
        """Validate custom date range if duration_type is custom"""
        if data.get('duration_type') == 'custom':
            if not data.get('service_start_date') or not data.get('service_end_date'):
                raise serializers.ValidationError({
                    'duration_type': 'service_start_date and service_end_date are required for custom duration'
                })
            if data['service_end_date'] < data['service_start_date']:
                raise serializers.ValidationError({
                    'service_end_date': 'End date must be after start date'
                })
        return data


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
            'preferred_date', 'preferred_time', 'created_at', 'worker_accepted',
            'client_rating', 'client_review',
            'total_price', 'duration_days', 'duration_type', 'estimated_duration_hours',
            'workers_needed',  # NEW: Multiple workers support
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


# NEW: Multiple Workers Assignment Serializers

class ServiceRequestAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for individual worker assignments"""
    worker_name = serializers.CharField(source='worker.user.get_full_name', read_only=True)
    worker_phone = serializers.CharField(source='worker.user.phone_number', read_only=True)
    worker_rating = serializers.DecimalField(source='worker.average_rating', max_digits=3, decimal_places=2, read_only=True)
    service_title = serializers.CharField(source='service_request.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True, allow_null=True)
    
    # NEW: Add flattened service request fields for mobile app compatibility
    title = serializers.CharField(source='service_request.title', read_only=True)
    description = serializers.CharField(source='service_request.description', read_only=True)
    category_name = serializers.CharField(source='service_request.category.name', read_only=True)
    urgency = serializers.CharField(source='service_request.urgency', read_only=True)
    location = serializers.CharField(source='service_request.location', read_only=True)
    city = serializers.CharField(source='service_request.city', read_only=True)
    preferred_date = serializers.DateField(source='service_request.preferred_date', read_only=True)
    preferred_time = serializers.TimeField(source='service_request.preferred_time', read_only=True)
    estimated_duration_hours = serializers.DecimalField(source='service_request.estimated_duration_hours', max_digits=5, decimal_places=2, read_only=True)
    client_name = serializers.CharField(source='service_request.client.get_full_name', read_only=True)
    client_phone = serializers.CharField(source='service_request.client.phone_number', read_only=True)
    client_email = serializers.CharField(source='service_request.client.email', read_only=True)
    client_notes = serializers.CharField(source='service_request.client_notes', read_only=True)
    created_at = serializers.DateTimeField(source='service_request.created_at', read_only=True)
    total_price = serializers.DecimalField(source='service_request.total_price', max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    
    class Meta:
        model = ServiceRequestAssignment
        fields = [
            'id', 'service_request', 'service_title', 'worker', 'worker_name', 
            'worker_phone', 'worker_rating', 'assigned_by', 'assigned_by_name',
            'assignment_number', 'status', 'status_display',
            'worker_accepted', 'worker_response_at', 'worker_rejection_reason',
            'work_started_at', 'work_completed_at', 'completion_notes',
            'worker_payment', 'total_hours_worked', 'admin_notes',
            'assigned_at', 'updated_at',
            # Flattened service request fields for mobile app
            'title', 'description', 'category_name', 'urgency', 'location', 'city',
            'preferred_date', 'preferred_time', 'estimated_duration_hours',
            'client_name', 'client_phone', 'client_email', 'client_notes', 'created_at',
            'total_price'
        ]
        read_only_fields = [
            'assigned_by', 'worker_response_at', 'work_started_at', 
            'work_completed_at', 'total_hours_worked', 'assigned_at', 'updated_at'
        ]


class BulkAssignWorkersSerializer(serializers.Serializer):
    """Serializer for admin assigning multiple workers at once"""
    worker_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100,
        help_text="List of worker IDs to assign"
    )
    admin_notes = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Optional notes for all assignments"
    )
    
    def validate_worker_ids(self, value):
        """Validate all worker IDs exist and are eligible"""
        # Remove duplicates
        worker_ids = list(set(value))
        
        # Check all workers exist and are verified
        workers = WorkerProfile.objects.filter(id__in=worker_ids)
        
        if workers.count() != len(worker_ids):
            raise serializers.ValidationError("One or more worker IDs are invalid.")
        
        # Check verification status
        for worker in workers:
            if worker.verification_status != 'verified':
                raise serializers.ValidationError(
                    f"Worker '{worker.user.get_full_name()}' must be verified to be assigned."
                )
        
        return worker_ids
    
    def validate(self, data):
        """Validate that number of workers doesn't exceed request needs"""
        service_request = self.context.get('service_request')
        if service_request:
            workers_count = len(data['worker_ids'])
            if workers_count > service_request.workers_needed:
                raise serializers.ValidationError({
                    'worker_ids': f"Cannot assign {workers_count} workers. Only {service_request.workers_needed} needed."
                })
        
        return data


class AssignmentResponseSerializer(serializers.Serializer):
    """Serializer for worker responding to assignment"""
    accepted = serializers.BooleanField(required=True)
    rejection_reason = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Required if accepted=False"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional notes when accepting assignment"
    )
    
    def validate(self, data):
        if not data['accepted'] and not data.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when declining assignment.'
            })
        return data


class ClientStatsSerializer(serializers.Serializer):
    """Serializer for client statistics"""
    total_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    in_progress_requests = serializers.IntegerField()
    completed_requests = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
