from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import authenticate, get_user_model
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from .serializers import UserSerializer, LoginSerializer, RegisterSerializer

User = get_user_model()


class LoginRateThrottle(AnonRateThrottle):
    """Reasonable rate limiting for login attempts"""
    rate = '20/minute'  # Increased from 5/minute


class RegisterRateThrottle(AnonRateThrottle):
    """Reasonable rate limiting for registration"""
    rate = '10/minute'  # Increased from 3/minute


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    from .login_lookup import authenticate_identifier, AMBIGUOUS

    # Email (any capitalisation), username or phone number in any format.
    user = authenticate_identifier(
        request,
        serializer.validated_data['identifier'],
        serializer.validated_data['password'],
    )
    if user == AMBIGUOUS:
        return Response(
            {'message': 'More than one account uses this phone number. Please log in with your email or username.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    if user is None:
        return Response(
            {'message': 'Invalid email, username, phone number or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)
    
    user_serializer = UserSerializer(user)
    
    # Check if profile is complete (for workers)
    is_complete = True
    completion_percentage = 100
    worker_type = None
    needs_setup = False
    if user.user_type == 'worker' and hasattr(user, 'worker_profile'):
        is_complete = user.worker_profile.is_profile_complete
        completion_percentage = user.worker_profile.profile_completion_percentage
        # the app shows Browse Jobs to professionals only - it needs this right away
        worker_type = user.worker_profile.worker_type
        # Profile Setup is for uploading the ID; once it is on file the worker
        # goes to the dashboard (which shows anything else still missing)
        needs_setup = not user.worker_profile.has_id_document
    
    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'userType': user.user_type,
            'phoneNumber': user.phone_number,
            'isProfileComplete': is_complete,
            'profileCompletionPercentage': completion_percentage,
            'workerType': worker_type,
            'needsSetup': needs_setup,
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterRateThrottle])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.save()
    
    # Create token for the new user
    token = Token.objects.create(user=user)
    
    # Check if profile is complete (for workers)
    is_complete = True
    completion_percentage = 100
    worker_type = None
    needs_setup = False
    if user.user_type == 'worker' and hasattr(user, 'worker_profile'):
        is_complete = user.worker_profile.is_profile_complete
        completion_percentage = user.worker_profile.profile_completion_percentage
        # the app shows Browse Jobs to professionals only - it needs this right away
        worker_type = user.worker_profile.worker_type
        # Profile Setup is for uploading the ID; once it is on file the worker
        # goes to the dashboard (which shows anything else still missing)
        needs_setup = not user.worker_profile.has_id_document
    
    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'userType': user.user_type,
            'phoneNumber': user.phone_number,
            'isProfileComplete': is_complete,
            'profileCompletionPercentage': completion_percentage,
            'workerType': worker_type,
            'needsSetup': needs_setup,
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    # Stop this phone's push notifications for the account logging out -
    # otherwise the next person to use the phone kept receiving them.
    push_token = request.data.get('push_token') if hasattr(request, 'data') else None
    if push_token:
        from worker_connect.notification_models import PushToken
        PushToken.objects.filter(user=request.user, token=push_token).update(is_active=False)
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


@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_token_view(request):
    """
    Return CSRF token for clients using session authentication.
    
    This endpoint is useful for:
    - Web frontends that need CSRF protection with session auth
    - Testing tools that need to make authenticated requests
    
    For mobile apps using token authentication, CSRF is not required
    as TokenAuthentication is stateless and not vulnerable to CSRF.
    """
    csrf_token = get_token(request)
    return Response({
        'csrfToken': csrf_token,
        'cookieName': 'csrftoken',
        'headerName': 'X-CSRFToken',
    })


# Password Reset Views
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer, ChangePasswordSerializer
import logging

logger = logging.getLogger('api')


class PasswordResetThrottle(AnonRateThrottle):
    """Rate limiting for password reset to prevent abuse"""
    rate = '3/hour'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_request(request):
    """
    Request a password reset email.
    
    Sends an email with a reset link if the email exists.
    Always returns success to prevent email enumeration.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    
    try:
        user = User.objects.get(email__iexact=email)
        
        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # The website's reset page uses the same token generator, so the
        # link works from any phone. It used to point at FRONTEND_URL, which
        # is unset on the server, so every link went to localhost.
        from django.urls import reverse
        reset_url = request.build_absolute_uri(
            reverse('accounts:reset_password', kwargs={'uidb64': uid, 'token': token})
        )
        
        # Send email
        send_mail(
            subject='Password Reset Request - Worker Connect',
            message=f'''
Hello {user.first_name},

You requested a password reset for your Worker Connect account.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you didn't request this reset, please ignore this email.

Best regards,
Worker Connect Team
            ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent to {email}")
        
    except User.DoesNotExist:
        # Don't reveal that the email doesn't exist
        logger.info(f"Password reset requested for non-existent email: {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
    
    # Always return success to prevent email enumeration
    return Response({
        'message': 'If an account exists with this email, a password reset link has been sent.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_confirm(request):
    """
    Confirm password reset with token and set new password.
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Parse the token (format: uid:token)
    token_data = serializer.validated_data['token']
    
    try:
        # Token should be in format "uid:token"
        uid, token = token_data.split(':')
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
        
        # Verify token
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Invalid or expired reset token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(serializer.validated_data['password'])
        user.save()
        
        # Invalidate all existing tokens
        Token.objects.filter(user=user).delete()
        
        logger.info(f"Password reset successful for user: {user.email}")
        
        return Response({
            'message': 'Password has been reset successfully. Please login with your new password.'
        })
        
    except (ValueError, User.DoesNotExist):
        return Response(
            {'error': 'Invalid reset token'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Password reset confirmation failed: {e}")
        return Response(
            {'error': 'Password reset failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change password for authenticated user.
    """
    serializer = ChangePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    # Verify current password
    if not user.check_password(serializer.validated_data['current_password']):
        return Response(
            {'current_password': ['Current password is incorrect.']},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Set new password
    user.set_password(serializer.validated_data['new_password'])
    user.save()
    
    # Invalidate all tokens except current one
    Token.objects.filter(user=user).exclude(key=request.auth.key).delete()
    
    logger.info(f"Password changed for user: {user.email}")
    
    return Response({
        'message': 'Password changed successfully.'
    })


# =============================================
# Session Management Endpoints
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_sessions(request):
    """
    Get list of active sessions (tokens) for the authenticated user.
    Returns all tokens with metadata about device/activity.
    """
    user = request.user
    current_token = request.auth.key if request.auth else None
    
    tokens = Token.objects.filter(user=user)
    sessions = []
    
    for token in tokens:
        sessions.append({
            'id': token.key[:8] + '...',  # Partial token for identification
            'created': token.created.isoformat(),
            'is_current': token.key == current_token,
        })
    
    return Response({
        'sessions': sessions,
        'total_sessions': len(sessions)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_session(request):
    """
    Revoke a specific session (token) by its partial ID.
    Cannot revoke the current session.
    """
    session_id = request.data.get('session_id')
    
    if not session_id:
        return Response(
            {'error': 'session_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    current_token = request.auth.key if request.auth else None
    
    # Find token that starts with the session_id
    tokens = Token.objects.filter(user=user)
    target_token = None
    
    for token in tokens:
        if token.key.startswith(session_id.replace('...', '')):
            target_token = token
            break
    
    if not target_token:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if target_token.key == current_token:
        return Response(
            {'error': 'Cannot revoke current session. Use logout instead.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    target_token.delete()
    logger.info(f"Session revoked for user: {user.email}")
    
    return Response({
        'message': 'Session revoked successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_all_sessions(request):
    """
    Revoke all sessions except the current one.
    Useful for security - "log out everywhere else".
    """
    user = request.user
    current_token = request.auth.key if request.auth else None
    
    # Keep current password to verify this is intentional
    password = request.data.get('password')
    if not password:
        return Response(
            {'error': 'Password is required to revoke all sessions'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not user.check_password(password):
        return Response(
            {'error': 'Invalid password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Delete all tokens except current
    deleted_count = Token.objects.filter(user=user).exclude(key=current_token).delete()[0]
    
    logger.info(f"Revoked {deleted_count} sessions for user: {user.email}")
    
    return Response({
        'message': f'Revoked {deleted_count} session(s) successfully',
        'sessions_revoked': deleted_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_account_activity(request):
    """
    Get account activity summary for the authenticated user.
    Includes login info, profile updates, etc.
    """
    user = request.user
    
    activity = {
        'user_id': user.id,
        'email': user.email,
        'date_joined': user.date_joined.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'is_active': user.is_active,
        'user_type': user.user_type,
        'active_sessions': Token.objects.filter(user=user).count(),
    }
    
    # Add profile-specific info for workers
    if user.user_type == 'worker' and hasattr(user, 'worker_profile'):
        profile = user.worker_profile
        activity['profile'] = {
            'is_complete': profile.is_profile_complete,
            'completion_percentage': profile.profile_completion_percentage,
            'is_available': profile.availability == 'available',
            'updated_at': profile.updated_at.isoformat() if hasattr(profile, 'updated_at') else None,
        }
    
    # Add client-specific info
    if user.user_type == 'client' and hasattr(user, 'client_profile'):
        profile = user.client_profile
        activity['profile'] = {
            'company_name': profile.company_name if hasattr(profile, 'company_name') else None,
        }
    
    return Response(activity)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Get notifications for the authenticated user"""
    from worker_connect.notification_models import Notification
    from worker_connect.notification_serializers import NotificationSerializer
    
    # The app sends is_read=false (it expected worker_connect's view, but
    # this one answers /api/notifications/ first) - accept both spellings.
    unread_only = (request.GET.get('unread_only', 'false').lower() == 'true'
                   or request.GET.get('is_read', '').lower() == 'false')
    try:
        limit = min(max(int(request.GET.get('limit', 50)), 1), 200)
    except ValueError:
        limit = 50
    
    # Query notifications from database (use recipient field from worker_connect model)
    notifications = Notification.objects.filter(recipient=request.user)
    
    if unread_only:
        notifications = notifications.filter(is_read=False)
    
    # Apply limit
    notifications = notifications[:limit]
    
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    from worker_connect.notification_models import Notification
    from django.shortcuts import get_object_or_404
    
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    
    return Response({'message': 'Notification marked as read', 'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all notifications as read for the user"""
    from worker_connect.notification_models import Notification
    from django.utils import timezone
    
    # Update all unread notifications (use recipient field from worker_connect model)
    updated_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return Response({
        'message': 'All notifications marked as read',
        'success': True,
        'count': updated_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_notification_count(request):
    """Get count of unread notifications"""
    from worker_connect.notification_models import Notification
    
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return Response({'count': count})
