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
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    profile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkerProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name', 'phone_number',
            'worker_type', 'bio', 'profile_image', 'hourly_rate', 'city', 'state', 'country', 'postal_code',
            'availability', 'verification_status', 'average_rating', 'address', 'religion',
            'can_work_everywhere', 'total_jobs', 'completed_jobs', 'total_earnings', 
            'categories', 'category_ids', 'experience_years', 'is_featured', 
            'created_at', 'updated_at', 'profile_completion_percentage', 
            'is_profile_complete', 'has_uploaded_national_id'
        ]
        read_only_fields = ['average_rating', 'total_jobs', 'completed_jobs', 'total_earnings', 
                           'verification_status', 'is_featured', 'profile_completion_percentage', 
                           'is_profile_complete', 'has_uploaded_national_id']
    
    def get_profile_image(self, obj):
        """Return full URL for profile image"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            # Fallback for local development
            return f"http://10.0.2.2:8000{obj.profile_image.url}"
        return None
    
    def update(self, instance, validated_data):
        category_ids = validated_data.pop('category_ids', None)
        
        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update categories if provided
        if category_ids is not None:
            instance.categories.set(category_ids)
        
        return instance
