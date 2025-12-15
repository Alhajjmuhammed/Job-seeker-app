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

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['firstName'],
            last_name=validated_data['lastName'],
            phone_number=validated_data['phone'],
            user_type=validated_data['userType'],
        )
        return user
