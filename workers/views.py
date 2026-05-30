from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import (WorkerProfile, WorkerDocument, WorkExperience, Category,
                     WorkerCustomSkill, WorkerCustomCategory)
from .forms import WorkerProfileForm, WorkerDocumentForm, WorkExperienceForm


@login_required
def worker_dashboard(request):
    """Worker dashboard view"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied. Workers only.')
        return redirect('home')
    
    profile, created = WorkerProfile.objects.get_or_create(user=request.user)
    
    context = {
        'profile': profile,
        'recent_documents': profile.documents.all()[:5],
        'experiences': profile.experiences.all()[:3],
        'custom_categories': WorkerCustomCategory.objects.filter(worker=profile),
        'custom_skills': WorkerCustomSkill.objects.filter(worker=profile),
    }
    return render(request, 'workers/dashboard.html', context)


@login_required
def profile_setup(request):
    """Initial profile setup for new workers"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile, created = WorkerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = WorkerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile created successfully!')
            return redirect('workers:dashboard')
    else:
        form = WorkerProfileForm(instance=profile)
    
    return render(request, 'workers/profile_setup.html', {'form': form, 'profile': profile})


@login_required
def profile_edit(request):
    """Edit worker profile"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    
    if request.method == 'POST':
        form = WorkerProfileForm(request.POST, instance=profile)
        phone_number = request.POST.get('phone_number', '')
        
        if form.is_valid():
            form.save()
            # Update phone number in User model
            if phone_number:
                request.user.phone_number = phone_number
                request.user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('workers:dashboard')
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = WorkerProfileForm(instance=profile)
    
    # Get custom skills and categories
    custom_skills = profile.custom_skills.all()
    custom_categories = profile.custom_categories.all()
    
    # Create forms for adding new custom items
    from .forms import CustomSkillForm, CustomCategoryForm, ProfileImageForm
    custom_skill_form = CustomSkillForm()
    custom_category_form = CustomCategoryForm()
    profile_image_form = ProfileImageForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
        'profile_image_form': profile_image_form,
        'custom_skills': custom_skills,
        'custom_categories': custom_categories,
        'custom_skill_form': custom_skill_form,
        'custom_category_form': custom_category_form,
    }
    return render(request, 'workers/profile_edit.html', context)


@login_required
def profile_image_upload(request):
    """Upload profile image separately"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    
    if request.method == 'POST':
        from .forms import ProfileImageForm
        form = ProfileImageForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile image updated successfully!')
        else:
            messages.error(request, 'Error uploading image. Please try again.')
    
    return redirect('workers:profile_edit')


@login_required
def profile_image_remove(request):
    """Remove profile image"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')

    profile = get_object_or_404(WorkerProfile, user=request.user)
    if profile.profile_image:
        profile.profile_image.delete(save=False)
        profile.profile_image = None
        profile.save()
        messages.success(request, 'Profile image removed.')
    else:
        messages.info(request, 'No profile image to remove.')
    return redirect('workers:profile_edit')


@login_required
def document_list(request):
    """List all worker documents"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    documents = profile.documents.all()
    
    return render(request, 'workers/document_list.html', {'documents': documents, 'profile': profile})


@login_required
def document_upload(request):
    """Upload a new document"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    
    if request.method == 'POST':
        form = WorkerDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.worker = profile
            document.save()
            messages.success(request, 'Document uploaded successfully! Awaiting verification.')
            return redirect('workers:document_list')
    else:
        form = WorkerDocumentForm()
    
    return render(request, 'workers/document_upload.html', {'form': form, 'profile': profile})


@login_required
def document_delete(request, pk):
    """Delete a document"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    document = get_object_or_404(WorkerDocument, pk=pk, worker=profile)
    
    if request.method == 'POST':
        document.file.delete()
        document.delete()
        messages.success(request, 'Document deleted successfully!')
        return redirect('workers:document_list')
    
    return render(request, 'workers/document_delete.html', {'document': document, 'profile': profile})


@login_required
def experience_list(request):
    """List work experiences"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    experiences = profile.experiences.all()
    
    return render(request, 'workers/experience_list.html', {'experiences': experiences, 'profile': profile})


@login_required
def experience_add(request):
    """Add work experience"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    
    if request.method == 'POST':
        form = WorkExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.worker = profile
            experience.save()
            messages.success(request, 'Experience added successfully!')
            return redirect('workers:experience_list')
    else:
        form = WorkExperienceForm()
    
    return render(request, 'workers/experience_form.html', {'form': form, 'action': 'Add', 'profile': profile})


@login_required
def experience_edit(request, pk):
    """Edit work experience"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    experience = get_object_or_404(WorkExperience, pk=pk, worker=profile)
    
    if request.method == 'POST':
        form = WorkExperienceForm(request.POST, instance=experience)
        if form.is_valid():
            form.save()
            messages.success(request, 'Experience updated successfully!')
            return redirect('workers:experience_list')
    else:
        form = WorkExperienceForm(instance=experience)
    
    return render(request, 'workers/experience_form.html', {'form': form, 'action': 'Edit', 'profile': profile})


@login_required
def experience_delete(request, pk):
    """Delete work experience"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    experience = get_object_or_404(WorkExperience, pk=pk, worker=profile)
    
    if request.method == 'POST':
        experience.delete()
        messages.success(request, 'Experience deleted successfully!')
        return redirect('workers:experience_list')
    
    return render(request, 'workers/experience_delete.html', {'experience': experience, 'profile': profile})


def worker_public_profile(request, pk):
    """Public view of worker profile (for clients)"""
    profile = get_object_or_404(WorkerProfile, pk=pk)
    
    context = {
        'profile': profile,
        'experiences': profile.experiences.all(),
        'categories': profile.categories.all(),
        'skills': profile.skills.all(),
    }
    return render(request, 'workers/public_profile.html', context)


@login_required
def custom_skill_add(request):
    """Add custom skill with optional certificate"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    
    if request.method == 'POST':
        from .forms import CustomSkillForm
        form = CustomSkillForm(request.POST, request.FILES)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.worker = profile
            skill.save()
            messages.success(request, f'Custom skill "{skill.name}" added successfully!')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    
    return redirect('workers:profile_edit')


@login_required
def custom_skill_delete(request, pk):
    """Delete custom skill"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    from .models import WorkerCustomSkill
    skill = get_object_or_404(WorkerCustomSkill, pk=pk, worker=profile)
    
    skill.delete()
    messages.success(request, f'Skill "{skill.name}" removed successfully!')
    return redirect('workers:profile_edit')


@login_required
def custom_category_add(request):
    """Add custom category"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    
    if request.method == 'POST':
        from .forms import CustomCategoryForm
        form = CustomCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.worker = profile
            category.save()
            messages.success(request, f'Custom category "{category.name}" added successfully!')
        else:
            # Show form errors for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return redirect('workers:profile_edit')


@login_required
def custom_category_delete(request, pk):
    """Delete custom category"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    from .models import WorkerCustomCategory
    category = get_object_or_404(WorkerCustomCategory, pk=pk, worker=profile)
    
    category.delete()
    messages.success(request, f'Category "{category.name}" removed successfully!')
    return redirect('workers:profile_edit')


@login_required
def worker_analytics(request):
    """Worker analytics dashboard view"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied. Workers only.')
        return redirect('home')
    
    from django.db.models import Sum, Avg, Count
    from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
    from jobs.service_request_models import ServiceRequest
    import json
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    
    # Get period filter (default: 180 days for 6 months)
    period = request.GET.get('period', '180')
    try:
        period_days = int(period)
    except ValueError:
        period_days = 180
    
    # Get all service requests for this worker
    all_requests = ServiceRequest.objects.filter(assigned_worker=profile)
    completed_requests = all_requests.filter(status='completed')
    
    # Apply period filter
    from datetime import datetime, timedelta
    period_start = datetime.now() - timedelta(days=period_days)
    filtered_completed = completed_requests.filter(updated_at__gte=period_start)
    filtered_all = all_requests.filter(updated_at__gte=period_start)
    
    # Basic stats (for selected period)
    total_assignments = filtered_all.count()
    completed_jobs = filtered_completed.count()
    active_jobs = all_requests.filter(status='in_progress').count()  # Current active jobs (not period filtered)
    
    # Earnings
    total_earnings = filtered_completed.aggregate(total=Sum('total_price'))['total'] or 0
    pending_earnings = all_requests.filter(status='in_progress').aggregate(total=Sum('total_price'))['total'] or 0
    
    # Performance metrics
    success_rate = (completed_jobs / total_assignments * 100) if total_assignments > 0 else 0
    avg_rating = filtered_completed.filter(client_rating__isnull=False).aggregate(avg=Avg('client_rating'))['avg'] or 0
    
    # Earnings by month, week, or day depending on period
    if period_days <= 30:
        # Last 30 days - show daily
        time_earnings = filtered_completed.annotate(
            time_period=TruncDay('updated_at')
        ).values('time_period').annotate(
            earnings=Sum('total_price'),
            jobs=Count('id')
        ).order_by('time_period')
    elif period_days <= 90:
        # Last 90 days - show weekly
        time_earnings = filtered_completed.annotate(
            time_period=TruncWeek('updated_at')
        ).values('time_period').annotate(
            earnings=Sum('total_price'),
            jobs=Count('id')
        ).order_by('time_period')
    else:
        # 180+ days - show monthly
        time_earnings = filtered_completed.annotate(
            time_period=TruncMonth('updated_at')
        ).values('time_period').annotate(
            earnings=Sum('total_price'),
            jobs=Count('id')
        ).order_by('time_period')
    
    # Earnings by category
    category_earnings = filtered_completed.values(
        'category__name', 'category__icon'
    ).annotate(
        earnings=Sum('total_price'),
        jobs=Count('id')
    ).order_by('-earnings')[:10]
    
    # Job status distribution (pie chart data)
    status_distribution = all_requests.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Recent completed jobs
    recent_jobs = filtered_completed.select_related('category', 'client').order_by('-updated_at')[:10]
    
    # Convert time earnings to JSON-serializable format
    time_earnings_list = []
    for item in time_earnings:
        time_earnings_list.append({
            'time_period': item['time_period'].isoformat() if item['time_period'] else None,
            'earnings': float(item['earnings'] or 0),
            'jobs': item['jobs']
        })
    
    # Convert category earnings to JSON
    category_earnings_list = []
    for item in category_earnings:
        category_earnings_list.append({
            'name': item['category__name'] or 'Uncategorized',
            'icon': item['category__icon'] or '',
            'earnings': float(item['earnings'] or 0),
            'jobs': item['jobs']
        })
    
    # Convert status distribution to JSON
    status_distribution_list = []
    status_labels = {
        'pending': 'Pending',
        'assigned': 'Assigned',
        'in_progress': 'In Progress',
        'completed': 'Completed',
        'cancelled': 'Cancelled'
    }
    for item in status_distribution:
        status_distribution_list.append({
            'status': status_labels.get(item['status'], item['status']),
            'count': item['count']
        })
    
    context = {
        'profile': profile,
        'total_assignments': total_assignments,
        'completed_jobs': completed_jobs,
        'active_jobs': active_jobs,
        'total_earnings': total_earnings,
        'pending_earnings': pending_earnings,
        'success_rate': round(success_rate, 1),
        'avg_rating': round(avg_rating, 1),
        'time_earnings_json': json.dumps(time_earnings_list),
        'category_earnings_json': json.dumps(category_earnings_list),
        'status_distribution_json': json.dumps(status_distribution_list),
        'category_earnings': list(category_earnings),
        'recent_jobs': recent_jobs,
        'period_days': period_days,
    }
    
    return render(request, 'workers/analytics.html', context)


@login_required
def export_analytics_csv(request):
    """Export analytics data to CSV"""
    if not request.user.is_worker:
        messages.error(request, 'Access denied. Workers only.')
        return redirect('home')
    
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    from jobs.service_request_models import ServiceRequest
    
    profile = get_object_or_404(WorkerProfile, user=request.user)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="analytics_{profile.user.username}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Analytics Export'])
    writer.writerow(['Worker:', profile.user.get_full_name()])
    writer.writerow(['Export Date:', datetime.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow([])
    
    # Summary stats
    all_requests = ServiceRequest.objects.filter(assigned_worker=profile)
    completed_requests = all_requests.filter(status='completed')
    
    from django.db.models import Sum, Avg, Count
    total_assignments = all_requests.count()
    completed_jobs = completed_requests.count()
    total_earnings = completed_requests.aggregate(total=Sum('total_price'))['total'] or 0
    avg_rating = completed_requests.filter(client_rating__isnull=False).aggregate(avg=Avg('client_rating'))['avg'] or 0
    success_rate = (completed_jobs / total_assignments * 100) if total_assignments > 0 else 0
    
    writer.writerow(['Summary Statistics'])
    writer.writerow(['Total Assignments', total_assignments])
    writer.writerow(['Completed Jobs', completed_jobs])
    writer.writerow(['Success Rate (%)', f'{success_rate:.1f}'])
    writer.writerow(['Total Earnings (TSH)', f'{total_earnings:.2f}'])
    writer.writerow(['Average Rating', f'{avg_rating:.2f}'])
    writer.writerow([])
    
    # Completed jobs details
    writer.writerow(['Completed Jobs Details'])
    writer.writerow(['Job ID', 'Category', 'Client', 'Title', 'Earnings (TSH)', 'Rating', 'Completed Date'])
    
    for job in completed_requests.select_related('category', 'client').order_by('-updated_at'):
        writer.writerow([
            job.id,
            job.category.name if job.category else 'N/A',
            job.client.get_full_name(),
            job.title,
            f'{job.total_price:.2f}' if job.total_price else '0.00',
            job.client_rating if job.client_rating else 'N/A',
            job.updated_at.strftime('%Y-%m-%d') if job.updated_at else 'N/A'
        ])
    
    writer.writerow([])
    
    # Earnings by category
    category_earnings = completed_requests.values(
        'category__name'
    ).annotate(
        earnings=Sum('total_price'),
        jobs=Count('id')
    ).order_by('-earnings')
    
    writer.writerow(['Earnings by Category'])
    writer.writerow(['Category', 'Jobs', 'Total Earnings (TSH)', 'Avg per Job (TSH)'])
    
    for item in category_earnings:
        cat_name = item['category__name'] or 'Uncategorized'
        jobs_count = item['jobs']
        earnings = item['earnings'] or 0
        avg_per_job = earnings / jobs_count if jobs_count > 0 else 0
        
        writer.writerow([
            cat_name,
            jobs_count,
            f'{earnings:.2f}',
            f'{avg_per_job:.2f}'
        ])
    
    return response
