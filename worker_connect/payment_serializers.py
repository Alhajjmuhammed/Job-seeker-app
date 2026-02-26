"""
Payment serializers for Worker Connect.
"""

from rest_framework import serializers
from workers.models import Payment, WorkerEarning


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""
    
    client_name = serializers.CharField(source='client.company_name', read_only=True)
    worker_name = serializers.CharField(source='worker.user.get_full_name', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_number',
            'client_name',
            'worker_name', 
            'job_title',
            'amount',
            'platform_fee',
            'worker_amount',
            'status',
            'payment_type',
            'description',
            'created_at',
            'processed_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'payment_number',
            'platform_fee',
            'worker_amount',
            'created_at',
            'processed_at', 
            'completed_at',
        ]


class WorkerEarningSerializer(serializers.ModelSerializer):
    """Worker earning serializer"""
    
    job_title = serializers.CharField(source='job.title', read_only=True)
    client_name = serializers.CharField(source='job.client.company_name', read_only=True)
    payment_number = serializers.CharField(source='payment.payment_number', read_only=True)
    
    class Meta:
        model = WorkerEarning
        fields = [
            'id',
            'job_title',
            'client_name',
            'payment_number',
            'amount',
            'earned_at',
        ]
        read_only_fields = '__all__'