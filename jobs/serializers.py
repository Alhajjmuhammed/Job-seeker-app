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
    
    class Meta:
        model = JobRequest
        fields = [
            'id', 'title', 'description', 'category', 'location',
            'budget', 'duration', 'status', 'client_name', 'created_at'
        ]
    
    def get_client_name(self, obj):
        return f"{obj.client.first_name} {obj.client.last_name}"


class JobApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    client_name = serializers.SerializerMethodField()
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'job_title', 'client_name', 'status',
            'proposed_rate', 'cover_letter', 'created_at'
        ]
    
    def get_client_name(self, obj):
        return f"{obj.job.client.first_name} {obj.job.client.last_name}"
