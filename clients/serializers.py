from rest_framework import serializers
from .models import ClientProfile, Favorite, Rating
from workers.models import WorkerProfile, Category
from accounts.models import User


class ClientProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = ClientProfile
        fields = [
            'user_id', 'email', 'first_name', 'last_name', 'phone_number',
            'company_name', 'address', 'city', 'state', 'country', 'postal_code',
            'total_jobs_posted', 'total_spent', 'created_at', 'updated_at'
        ]
        read_only_fields = ['total_jobs_posted', 'total_spent', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'icon']


class WorkerSearchSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkerProfile
        fields = [
            'id', 'user_id', 'name', 'email', 'phone_number',
            'bio', 'hourly_rate', 'city', 'state', 'postal_code', 'profile_image',
            'availability', 'verification_status', 'average_rating',
            'total_reviews', 'completed_jobs', 'total_jobs', 'categories', 'is_favorite',
            'experience_years', 'worker_type', 'created_at'
        ]
    
    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(client=request.user, worker=obj).exists()
        return False
    
    def get_profile_image(self, obj):
        """Return full URL for profile image"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return None
        return None
    
    def get_total_reviews(self, obj):
        """Get total number of reviews for this worker"""
        return obj.ratings_received.count()


class RatingSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Rating
        fields = ['id', 'rating', 'review', 'client_name', 'created_at']
    
    def get_client_name(self, obj):
        return f"{obj.client.first_name} {obj.client.last_name}"


class FavoriteSerializer(serializers.ModelSerializer):
    worker = WorkerSearchSerializer(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'worker', 'created_at']
