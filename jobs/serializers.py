from rest_framework import serializers
from jobs.models import DirectHireRequest, JobRequest, JobApplication


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


class JobRequestSerializer(serializers.ModelSerializer):
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


class JobRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating job requests"""
    
    class Meta:
        model = JobRequest
        fields = [
            'title', 'description', 'category', 'location', 'city',
            'budget', 'duration_days', 'start_date', 'workers_needed', 'urgency'
        ]
    
    def create(self, validated_data):
        # Client is set from request.user in the view
        return JobRequest.objects.create(**validated_data)


class JobApplicationSerializer(serializers.ModelSerializer):
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


class JobApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating job applications"""
    
    class Meta:
        model = JobApplication
        fields = ['job', 'cover_letter', 'proposed_rate']
    
    def create(self, validated_data):
        # Worker is set from request in the view
        return JobApplication.objects.create(**validated_data)
