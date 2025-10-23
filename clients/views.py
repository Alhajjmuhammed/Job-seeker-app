from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from workers.models import WorkerProfile, Category
from .models import ClientProfile, Rating, Favorite
from .forms import ClientProfileForm, RatingForm


@login_required
def client_dashboard(request):
    """Client dashboard view"""
    if not request.user.is_client:
        messages.error(request, 'Access denied. Clients only.')
        return redirect('home')
    
    profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    # Get featured workers
    featured_workers = WorkerProfile.objects.filter(
        is_featured=True,
        verification_status='verified',
        availability='available'
    )[:6]
    
    # Get favorites
    favorites = Favorite.objects.filter(client=request.user).select_related('worker')[:5]
    
    context = {
        'profile': profile,
        'featured_workers': featured_workers,
        'favorites': favorites,
        'categories': Category.objects.filter(is_active=True)[:8],
    }
    return render(request, 'clients/dashboard.html', context)


@login_required
def search_workers(request):
    """Search and filter workers"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    workers = WorkerProfile.objects.filter(verification_status='verified')
    
    # Search query
    query = request.GET.get('q', '')
    if query:
        workers = workers.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(bio__icontains=query) |
            Q(city__icontains=query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    if category_id and category_id != 'None':
        workers = workers.filter(categories__id=category_id)
    
    # City filter
    city = request.GET.get('city', '').strip()
    if city and city != 'None':
        workers = workers.filter(city__icontains=city)
    
    # Availability filter
    availability = request.GET.get('availability')
    if availability and availability != 'None':
        workers = workers.filter(availability=availability)
    
    # Rating filter
    min_rating = request.GET.get('min_rating')
    if min_rating and min_rating != 'None':
        workers = workers.filter(average_rating__gte=min_rating)
    
    # Sorting
    sort_by = request.GET.get('sort', '-average_rating')
    workers = workers.order_by(sort_by).distinct()
    
    # Get user's favorite worker IDs
    user_favorites = list(Favorite.objects.filter(client=request.user).values_list('worker_id', flat=True))
    
    context = {
        'workers': workers,
        'categories': Category.objects.filter(is_active=True),
        'query': query,
        'selected_category': category_id,
        'selected_city': city,
        'selected_availability': availability,
        'selected_min_rating': min_rating,
        'selected_sort': sort_by,
        'user_favorites': user_favorites,
    }
    return render(request, 'clients/search_workers.html', context)


@login_required
def worker_detail(request, pk):
    """View detailed worker profile"""
    worker = get_object_or_404(WorkerProfile, pk=pk)
    
    is_favorite = False
    if request.user.is_authenticated and request.user.is_client:
        is_favorite = Favorite.objects.filter(client=request.user, worker=worker).exists()
    
    ratings = Rating.objects.filter(worker=worker).select_related('client').order_by('-created_at')
    total_ratings = ratings.count()
    
    # Combine regular and custom categories/skills
    all_categories = list(worker.categories.all()) + list(worker.custom_categories.all())
    all_skills = list(worker.skills.all()) + list(worker.custom_skills.all())
    
    context = {
        'worker': worker,
        'is_favorite': is_favorite,
        'ratings': ratings,
        'total_ratings': total_ratings,
        'experiences': worker.experiences.all(),
        'categories': all_categories,
        'skills': all_skills,
        'documents': worker.documents.filter(verification_status='approved'),  # Only show approved documents to clients
    }
    return render(request, 'clients/worker_detail.html', context)


@login_required
def toggle_favorite(request, pk):
    """Add or remove worker from favorites"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    worker = get_object_or_404(WorkerProfile, pk=pk)
    favorite, created = Favorite.objects.get_or_create(client=request.user, worker=worker)
    
    if not created:
        favorite.delete()
        messages.success(request, 'Worker removed from favorites.')
    else:
        messages.success(request, 'Worker added to favorites.')
    
    # Redirect back to the referring page or worker detail
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('clients:worker_detail', pk=pk)


@login_required
def favorites_list(request):
    """List all favorite workers"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    favorites = Favorite.objects.filter(client=request.user).select_related('worker')
    
    return render(request, 'clients/favorites_list.html', {'favorites': favorites})


@login_required
def rate_worker(request, pk):
    """Rate a worker"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    worker = get_object_or_404(WorkerProfile, pk=pk)
    
    # Check if already rated
    existing_rating = Rating.objects.filter(client=request.user, worker=worker).first()
    
    if request.method == 'POST':
        form = RatingForm(request.POST, instance=existing_rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.client = request.user
            rating.worker = worker
            rating.save()
            
            # Update worker's average rating
            avg_rating = Rating.objects.filter(worker=worker).aggregate(Avg('rating'))['rating__avg']
            worker.average_rating = round(avg_rating, 2) if avg_rating else 0
            worker.save()
            
            messages.success(request, 'Rating submitted successfully!')
            return redirect('clients:worker_detail', pk=pk)
    else:
        form = RatingForm(instance=existing_rating)
    
    context = {
        'form': form,
        'worker': worker,
        'existing_rating': existing_rating,
    }
    return render(request, 'clients/rate_worker.html', context)


@login_required
def profile_edit(request):
    """Edit client profile"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ClientProfileForm(request.POST, instance=profile)
        
        # Get phone number from POST data
        phone_number = request.POST.get('phone_number', '').strip()
        
        if form.is_valid():
            form.save()
            
            # Update user's phone number
            if phone_number:
                request.user.phone_number = phone_number
                request.user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('clients:profile')
    else:
        form = ClientProfileForm(instance=profile)
    
    return render(request, 'clients/profile_edit.html', {'form': form, 'profile': profile})


@login_required
def profile_view(request):
    """View client profile"""
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    # Get statistics
    from jobs.models import JobRequest
    total_jobs = JobRequest.objects.filter(client=request.user).count()
    open_jobs = JobRequest.objects.filter(client=request.user, status='open').count()
    in_progress_jobs = JobRequest.objects.filter(client=request.user, status='in_progress').count()
    completed_jobs = JobRequest.objects.filter(client=request.user, status='completed').count()
    
    # Recent jobs
    recent_jobs = JobRequest.objects.filter(client=request.user).order_by('-created_at')[:5]
    
    # Favorites count
    favorites_count = Favorite.objects.filter(client=request.user).count()
    
    # Recent ratings given
    recent_ratings = Rating.objects.filter(client=request.user).select_related('worker').order_by('-created_at')[:5]
    
    context = {
        'profile': profile,
        'total_jobs': total_jobs,
        'open_jobs': open_jobs,
        'in_progress_jobs': in_progress_jobs,
        'completed_jobs': completed_jobs,
        'recent_jobs': recent_jobs,
        'favorites_count': favorites_count,
        'recent_ratings': recent_ratings,
    }
    return render(request, 'clients/profile.html', context)
