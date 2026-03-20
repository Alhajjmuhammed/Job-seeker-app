from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .forms import (
    WorkerRegistrationForm, ClientRegistrationForm, CustomLoginForm, 
    ProfileUpdateForm, PasswordResetRequestForm, PasswordResetConfirmForm,
    ChangePasswordForm
)
from agents.forms import AgentRegistrationForm
from .models import User


def register_choice(request):
    """View to choose between worker or client registration"""
    return render(request, 'accounts/register_choice.html')


def worker_register(request):
    """Worker registration view"""
    if request.method == 'POST':
        form = WorkerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('workers:profile_setup')
    else:
        form = WorkerRegistrationForm()
    
    return render(request, 'accounts/worker_register.html', {'form': form})


def client_register(request):
    """Client registration view"""
    if request.method == 'POST':
        form = ClientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Worker Connect.')
            return redirect('clients:dashboard')
    else:
        form = ClientRegistrationForm()
    
    return render(request, 'accounts/client_register.html', {'form': form})


def agent_register(request):
    """Agent registration view"""
    if request.method == 'POST':
        form = AgentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Your application is under review by admin.')
            return redirect('agents:dashboard')
    else:
        form = AgentRegistrationForm()
    return render(request, 'accounts/agent_register.html', {'form': form})


def user_login(request):
    """Login view for all users"""
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Always redirect based on user type first (admin always goes to admin dashboard)
                if user.is_admin_user:
                    return redirect('admin_panel:dashboard')
                elif user.is_worker:
                    return redirect('workers:dashboard')
                elif user.is_client:
                    return redirect('clients:dashboard')
                elif user.is_agent:
                    return redirect('agents:dashboard')
                
                # Only use 'next' for non-role users
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                
                return redirect('home')
    else:
        form = CustomLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def user_logout(request):
    """Logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def profile_view(request):
    """View user profile - redirect to appropriate dashboard"""
    if request.user.is_worker:
        return redirect('workers:dashboard')
    elif request.user.is_client:
        return redirect('clients:dashboard')
    elif request.user.is_staff:
        return redirect('admin_panel:dashboard')
    elif request.user.is_agent:
        return redirect('agents:dashboard')
    else:
        return redirect('home')


@login_required
def profile_edit(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def notification_center(request):
    """Notification center view - list all notifications with filters"""
    from worker_connect.notification_models import Notification
    from django.core.paginator import Paginator
    
    # Get filter parameter
    filter_type = request.GET.get('filter', 'all')  # 'all' or 'unread'
    
    # Get all notifications for this user
    notifications = Notification.objects.filter(recipient=request.user).select_related(
        'content_type'
    ).order_by('-created_at')
    
    # Apply filter
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    
    # Get counts for filter badges
    all_count = Notification.objects.filter(recipient=request.user).count()
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    # Pagination
    paginator = Paginator(notifications, 20)  # 20 notifications per page
    page = request.GET.get('page', 1)
    notifications_page = paginator.get_page(page)
    
    context = {
        'notifications': notifications_page,
        'filter_type': filter_type,
        'all_count': all_count,
        'unread_count': unread_count,
    }
    
    return render(request, 'accounts/notification_center.html', context)


@login_required
def mark_notification_as_read_web(request, notification_id):
    """Mark a single notification as read (web version)"""
    from worker_connect.notification_models import Notification
    from django.shortcuts import get_object_or_404
    
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    
    messages.success(request, 'Notification marked as read.')
    return redirect('accounts:notification_center')


@login_required
def mark_all_notifications_read_web(request):
    """Mark all notifications as read (web version)"""
    from worker_connect.notification_models import Notification
    from django.utils import timezone
    
    if request.method == 'POST':
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        messages.success(request, f'{updated_count} notification(s) marked as read.')
    
    return redirect('accounts:notification_center')


def forgot_password(request):
    """Request password reset - sends email with reset link"""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Try to find user by email
            try:
                user = User.objects.get(email=email)
                
                # Generate token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build reset URL
                reset_url = request.build_absolute_uri(
                    f'/accounts/reset-password/{uid}/{token}/'
                )
                
                # Send email
                context = {
                    'user': user,
                    'reset_url': reset_url,
                    'site_name': 'Worker Connect',
                    'expiry_hours': 24,
                }
                
                html_message = render_to_string('emails/password_reset.html', context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject='Password Reset Request - Worker Connect',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                messages.success(
                    request, 
                    'If an account exists with this email, you will receive a password reset link shortly.'
                )
                return redirect('accounts:login')
                
            except User.DoesNotExist:
                # Don't reveal if user exists (security best practice)
                messages.success(
                    request, 
                    'If an account exists with this email, you will receive a password reset link shortly.'
                )
                return redirect('accounts:login')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'accounts/forgot_password.html', {'form': form})


def reset_password(request, uidb64, token):
    """Reset password using token from email"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data['password1']
                user.set_password(password)
                user.save()
                
                messages.success(request, 'Your password has been reset successfully. You can now log in.')
                return redirect('accounts:login')
        else:
            form = PasswordResetConfirmForm()
        
        return render(request, 'accounts/reset_password.html', {
            'form': form,
            'validlink': True
        })
    else:
        return render(request, 'accounts/reset_password.html', {
            'validlink': False
        })


@login_required
def change_password(request):
    """Change password for logged-in user"""
    if request.method == 'POST':
        form = ChangePasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            request.user.set_password(new_password)
            request.user.save()
            
            # Update session to prevent logout
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Your password has been changed successfully!')
            
            # Redirect based on user type
            if request.user.is_worker:
                return redirect('workers:dashboard')
            elif request.user.is_client:
                return redirect('clients:dashboard')
            else:
                return redirect('accounts:profile')
    else:
        form = ChangePasswordForm(user=request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

