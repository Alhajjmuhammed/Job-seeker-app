from rest_framework import serializers
from workers.models import WorkerProfile, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'icon']


class WorkerProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkerProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name', 'phone_number',
            'bio', 'hourly_rate', 'city', 'state', 'country', 'postal_code',
            'availability', 'verification_status', 'average_rating',
            'total_jobs', 'completed_jobs', 'total_earnings', 'categories',
            'experience_years', 'is_featured', 'created_at', 'updated_at'
        ]
        read_only_fields = ['average_rating', 'total_jobs', 'completed_jobs', 'total_earnings', 'verification_status', 'is_featured']
