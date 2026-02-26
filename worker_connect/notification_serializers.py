from rest_framework import serializers
from .notification_models import Notification, NotificationPreference, PushToken

class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'is_read',
            'created_at', 'read_at', 'extra_data', 'time_ago'
        ]
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        return timesince(obj.created_at, timezone.now())

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        exclude = ['user', 'id', 'created_at']

class PushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushToken
        fields = ['token', 'device_type', 'device_id', 'app_version']
        
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # Deactivate existing tokens for same device
        PushToken.objects.filter(
            user=validated_data['user'],
            device_type=validated_data['device_type'],
            device_id=validated_data.get('device_id', '')
        ).update(is_active=False)
        
        return super().create(validated_data)