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
    # token is unique in the table, and the model validator rejected every
    # repeat registration - the app registers on each start, and a phone
    # keeps its token when a different person logs in on it - so the token
    # stayed attached to whoever registered it first, or to nobody.
    token = serializers.CharField()

    class Meta:
        model = PushToken
        fields = ['token', 'device_type', 'device_id', 'app_version']
        
    def create(self, validated_data):
        user = self.context['request'].user
        # Deactivate existing tokens for same device
        PushToken.objects.filter(
            user=user,
            device_type=validated_data['device_type'],
            device_id=validated_data.get('device_id', '')
        ).exclude(token=validated_data['token']).update(is_active=False)

        # One phone, one token: it now belongs to whoever is logged in.
        token, _ = PushToken.objects.update_or_create(
            token=validated_data.pop('token'),
            defaults={**validated_data, 'user': user, 'is_active': True},
        )
        return token