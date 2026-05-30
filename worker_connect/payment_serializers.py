"""
Payment serializers for Worker Connect.
"""

from rest_framework import serializers
from workers.models import Payment, WorkerEarning, SavedCard, BankAccount, MobileMoneyAccount


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


class SavedCardSerializer(serializers.ModelSerializer):
    """Saved card serializer"""
    
    # Display fields
    card_display = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedCard
        fields = [
            'id',
            'card_type',
            'last_four',
            'expiry_month',
            'expiry_year',
            'cardholder_name',
            'card_display',
            'is_default',
            'is_active',
            'is_expired',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'card_display', 'is_expired']
    
    def get_card_display(self, obj):
        """Get formatted card display"""
        return f"{obj.card_type.upper()} ****{obj.last_four}"
    
    def get_is_expired(self, obj):
        """Check if card is expired"""
        from django.utils import timezone
        now = timezone.now()
        if obj.expiry_year < now.year:
            return True
        if obj.expiry_year == now.year and obj.expiry_month < now.month:
            return True
        return False


class BankAccountSerializer(serializers.ModelSerializer):
    """Bank account serializer"""
    
    # Display fields
    account_display = serializers.SerializerMethodField()
    
    class Meta:
        model = BankAccount
        fields = [
            'id',
            'bank_name',
            'account_holder_name',
            'account_number',
            'routing_number',
            'swift_code',
            'account_type',
            'account_display',
            'is_verified',
            'verified_at',
            'is_default',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'is_verified', 'verified_at', 'created_at', 'account_display']
        extra_kwargs = {
            'account_number': {'write_only': True},
            'routing_number': {'write_only': True},
        }
    
    def get_account_display(self, obj):
        """Get formatted account display (masked)"""
        if len(obj.account_number) > 4:
            return f"{obj.bank_name} - ****{obj.account_number[-4:]}"
        return f"{obj.bank_name} - {obj.account_number}"
    
    def to_representation(self, instance):
        """Mask sensitive data in response"""
        data = super().to_representation(instance)
        # Don't include full account number in response
        if 'account_number' in data:
            data['account_number'] = f"****{instance.account_number[-4:]}"
        return data


class MobileMoneyAccountSerializer(serializers.ModelSerializer):
    """Mobile money account serializer"""
    
    # Display fields
    account_display = serializers.SerializerMethodField()
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    
    class Meta:
        model = MobileMoneyAccount
        fields = [
            'id',
            'provider',
            'provider_display',
            'phone_number',
            'account_name',
            'account_display',
            'is_verified',
            'verified_at',
            'is_default',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'is_verified', 'verified_at', 'created_at', 'account_display', 'provider_display']
    
    def get_account_display(self, obj):
        """Get formatted account display"""
        return f"{obj.get_provider_display()} - {obj.phone_number}"