from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'phone_number']
        read_only_fields = ['id']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class RegisterSerializer(serializers.Serializer):
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    userType = serializers.ChoiceField(choices=['worker', 'client'])
    workerType = serializers.ChoiceField(choices=['professional', 'non-academic'], required=False, allow_null=True)

    def create(self, validated_data):
        worker_type = validated_data.pop('workerType', None)
        email = validated_data['email']
        
        # Use email as username since Django requires it
        user = User.objects.create_user(
            username=email,  # Use email as username
            email=email,
            password=validated_data['password'],
            first_name=validated_data['firstName'],
            last_name=validated_data['lastName'],
            phone_number=validated_data['phone'],
            user_type=validated_data['userType'],
        )
        
        # Create worker profile with worker_type if user is a worker
        if validated_data['userType'] == 'worker' and worker_type:
            from workers.models import WorkerProfile
            WorkerProfile.objects.create(
                user=user,
                worker_type='non_academic' if worker_type == 'non-academic' else 'professional',
                profile_completion_percentage=0,
                is_profile_complete=False,
            )
        
        return user
