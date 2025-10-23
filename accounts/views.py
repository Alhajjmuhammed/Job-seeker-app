from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .forms import WorkerRegistrationForm, ClientRegistrationForm, CustomLoginForm, ProfileUpdateForm
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
                
                # Redirect based on user type
                if user.is_worker:
                    return redirect('workers:dashboard')
                elif user.is_client:
                    return redirect('clients:dashboard')
                elif user.is_admin_user:
                    return redirect('admin_panel:dashboard')
                else:
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
