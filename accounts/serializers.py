from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

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
    firstName = serializers.CharField(min_length=1, max_length=150)
    lastName = serializers.CharField(min_length=1, max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(min_length=9, max_length=17)
    password = serializers.CharField(write_only=True, min_length=8)
    userType = serializers.ChoiceField(choices=['worker', 'client'])
    workerType = serializers.ChoiceField(choices=['professional', 'non-academic'], required=False, allow_null=True)

    def validate_email(self, value):
        """Check that email is not already in use"""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_password(self, value):
        """Validate password using Django's built-in validators"""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

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


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting password reset email."""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset with token."""
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    def validate_password(self, value):
        """Validate password using Django's built-in validators."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, data):
        """Check that passwords match."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password while logged in."""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    def validate_new_password(self, value):
        """Validate new password using Django's built-in validators."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, data):
        """Check that new passwords match."""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Passwords do not match.'
            })
        return data
