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
