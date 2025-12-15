from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from .serializers import UserSerializer, LoginSerializer, RegisterSerializer

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    # Look up user by email first
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'message': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Authenticate using username
    user = authenticate(request, username=user.username, password=password)
    
    if user is None:
        return Response(
            {'message': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)
    
    user_serializer = UserSerializer(user)
    
    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'userType': user.user_type,
            'phoneNumber': user.phone_number,
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user already exists
    if User.objects.filter(email=serializer.validated_data['email']).exists():
        return Response(
            {'message': 'User with this email already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = serializer.save()
    
    # Create token for the new user
    token = Token.objects.create(user=user)
    
    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'userType': user.user_type,
            'phoneNumber': user.phone_number,
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        # Delete the user's token
        request.user.auth_token.delete()
    except Exception as e:
        # Token might not exist or already deleted
        pass
    return Response({'message': 'Successfully logged out'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'firstName': user.first_name,
        'lastName': user.last_name,
        'userType': user.user_type,
        'phoneNumber': user.phone_number,
    })
