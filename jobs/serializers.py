from rest_framework import serializers
from jobs.models import DirectHireRequest, JobRequest, JobApplication
from worker_connect.serializer_mixins import SanitizedSerializerMixin


class DirectHireRequestSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectHireRequest
        fields = [
            'id', 'client_name', 'duration_type', 'offered_rate', 
            'total_amount', 'status', 'created_at', 'message'
        ]
    
    def get_client_name(self, obj):
        return f"{obj.client.first_name} {obj.client.last_name}"


class JobRequestSerializer(SanitizedSerializerMixin, serializers.ModelSerializer):
    """Job request serializer with input sanitization"""
    
    sanitize_fields = ['title', 'description', 'location', 'city']
    
    client_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    application_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = JobRequest
        fields = [
            'id', 'title', 'description', 'category', 'category_name', 'location', 'city',
            'budget', 'duration_days', 'start_date', 'workers_needed', 'status', 'urgency',
            'client_name', 'created_at', 'updated_at', 'application_count'
        ]
        read_only_fields = ['client_name', 'created_at', 'updated_at', 'application_count']
    
    def get_client_name(self, obj):
        return f"{obj.client.first_name} {obj.client.last_name}"


class JobRequestCreateSerializer(SanitizedSerializerMixin, serializers.ModelSerializer):
    """Serializer for creating job requests with input sanitization"""
    
    sanitize_fields = ['title', 'description', 'location', 'city']
    
    class Meta:
        model = JobRequest
        fields = [
            'title', 'description', 'category', 'location', 'city',
            'budget', 'duration_days', 'start_date', 'workers_needed', 'urgency'
        ]
    
    def validate_budget(self, value):
        """Validate budget is positive"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Budget must be a positive number")
        if value is not None and value > 1000000:
            raise serializers.ValidationError("Budget cannot exceed 1,000,000")
        return value
    
    def validate_workers_needed(self, value):
        """Validate workers_needed is within reasonable range"""
        if value < 1:
            raise serializers.ValidationError("At least 1 worker is required")
        if value > 100:
            raise serializers.ValidationError("Cannot request more than 100 workers")
        return value
    
    def validate_duration_days(self, value):
        """Validate duration_days is positive"""
        if value is not None and value < 1:
            raise serializers.ValidationError("Duration must be at least 1 day")
        if value is not None and value > 365:
            raise serializers.ValidationError("Duration cannot exceed 365 days")
        return value
    
    def create(self, validated_data):
        # Client is set from request.user in the view
        return JobRequest.objects.create(**validated_data)


class JobApplicationSerializer(SanitizedSerializerMixin, serializers.ModelSerializer):
    """Job application serializer with input sanitization"""
    
    sanitize_fields = ['cover_letter']
    
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_id = serializers.IntegerField(source='job.id', read_only=True)
    client_name = serializers.SerializerMethodField()
    worker_name = serializers.SerializerMethodField()
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'job_id', 'job_title', 'client_name', 'worker_name', 
            'status', 'proposed_rate', 'cover_letter', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_client_name(self, obj):
        return f"{obj.job.client.first_name} {obj.job.client.last_name}"
    
    def get_worker_name(self, obj):
        return f"{obj.worker.user.first_name} {obj.worker.user.last_name}"


class JobApplicationCreateSerializer(SanitizedSerializerMixin, serializers.ModelSerializer):
    """Serializer for creating job applications with input sanitization"""
    
    sanitize_fields = ['cover_letter']
    
    class Meta:
        model = JobApplication
        fields = ['job', 'cover_letter', 'proposed_rate']
    
    def create(self, validated_data):
        # Worker is set from request in the view
        return JobApplication.objects.create(**validated_data)
