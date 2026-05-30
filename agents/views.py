import json
from datetime import date
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models.functions import TruncMonth
from django.db.models import Count

from django.contrib.auth import update_session_auth_hash
from .models import AgentProfile
from .forms import AgentProfileForm, AgentCreateWorkerForm
from accounts.forms import ChangePasswordForm
from workers.models import WorkerProfile


def agent_required(view_func):
    """Decorator: only verified agents can access."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'agent_profile'):
            messages.error(request, 'Access denied. Agent account required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@agent_required
def dashboard(request):
    """Agent dashboard overview."""
    agent = request.user.agent_profile
    workers = agent.workers.select_related('user').all()

    verified_count = workers.filter(verification_status='verified').count()
    pending_count = workers.filter(verification_status='pending').count()
    rejected_count = workers.filter(verification_status='rejected').count()

    # Top 6 workers by completed jobs
    top_workers = list(
        workers.order_by('-completed_jobs')[:6]
        .values('user__first_name', 'user__last_name', 'user__username', 'completed_jobs')
    )
    top_labels = [w['user__first_name'] or w['user__username'] for w in top_workers]
    top_jobs = [w['completed_jobs'] for w in top_workers]

    # Workers joined per month (last 6 months)
    today = date.today()
    months, joined_counts = [], []
    for i in range(5, -1, -1):
        d = today - relativedelta(months=i)
        months.append(d.strftime('%b %Y'))
        joined_counts.append(
            workers.filter(created_at__year=d.year, created_at__month=d.month).count()
        )

    context = {
        'agent': agent,
        'workers': workers,
        'total_workers': workers.count(),
        'verified_workers': verified_count,
        'pending_workers': pending_count,
        'rejected_workers': rejected_count,
        'total_jobs': sum(w.completed_jobs for w in workers),
        # Chart data (JSON)
        'donut_data': json.dumps([verified_count, pending_count, rejected_count]),
        'top_labels': json.dumps(top_labels),
        'top_jobs': json.dumps(top_jobs),
        'months_labels': json.dumps(months),
        'joined_counts': json.dumps(joined_counts),
    }
    return render(request, 'agents/dashboard.html', context)


@agent_required
def my_workers(request):
    """List of workers managed by this agent."""
    agent = request.user.agent_profile
    workers = agent.workers.select_related('user').all()
    return render(request, 'agents/workers.html', {
        'agent': agent,
        'workers': workers,
        'create_form': AgentCreateWorkerForm(),
    })


@agent_required
def search_workers(request):
    """Search for workers not yet linked to any agent."""
    agent = request.user.agent_profile
    if not agent.is_verified:
        messages.error(request, 'Your account must be verified before adding workers.')
        return redirect('agents:workers')

    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = (
            WorkerProfile.objects
            .filter(agent__isnull=True)
            .filter(
                models.Q(user__username__icontains=query) |
                models.Q(user__email__icontains=query) |
                models.Q(user__first_name__icontains=query) |
                models.Q(user__last_name__icontains=query)
            )
            .select_related('user')[:20]
        )
    return render(request, 'agents/search_workers.html', {
        'agent': agent,
        'query': query,
        'results': results,
    })


@agent_required
def add_worker(request, worker_id):
    """Link an existing worker to this agent."""
    from django.views.decorators.http import require_http_methods
    agent = request.user.agent_profile
    if not agent.is_verified:
        messages.error(request, 'Your account must be verified before adding workers.')
        return redirect('agents:workers')

    if request.method != 'POST':
        return redirect('agents:search_workers')

    worker = get_object_or_404(WorkerProfile, id=worker_id)
    if worker.agent is not None and worker.agent != agent:
        messages.error(request, 'This worker is already linked to another agent.')
    elif worker.agent == agent:
        messages.info(request, 'This worker is already in your team.')
    else:
        worker.agent = agent
        worker.save()
        messages.success(request, f'{worker.user.get_full_name() or worker.user.username} added to your team.')
    return redirect('agents:workers')


@agent_required
def remove_worker(request, worker_id):
    """Remove a worker from this agent."""
    agent = request.user.agent_profile
    if request.method != 'POST':
        return redirect('agents:workers')

    worker = get_object_or_404(WorkerProfile, id=worker_id, agent=agent)
    worker.agent = None
    worker.save()
    messages.success(request, f'{worker.user.get_full_name() or worker.user.username} removed from your team.')
    return redirect('agents:workers')


@agent_required
def create_worker(request):
    """Agent creates a brand-new worker account and links them directly."""
    agent = request.user.agent_profile
    if not agent.is_verified:
        messages.error(request, 'Your account must be verified before adding workers.')
        return redirect('agents:workers')

    if request.method == 'POST':
        form = AgentCreateWorkerForm(request.POST)
        if form.is_valid():
            worker_user = form.save(commit=False)
            worker_user.user_type = 'worker'
            worker_user.save()
            profile, _ = WorkerProfile.objects.get_or_create(user=worker_user)
            profile.agent = agent
            profile.save()
            messages.success(
                request,
                f'Worker account for {worker_user.get_full_name() or worker_user.username} created and added to your team.'
            )
            return redirect('agents:workers')
        # On error: re-render workers page with modal open
        workers = agent.workers.select_related('user').all()
        return render(request, 'agents/workers.html', {
            'agent': agent,
            'workers': workers,
            'create_form': form,
            'show_create_modal': True,
        })
    return redirect('agents:workers')


@agent_required
def profile(request):
    """Agent profile view/edit."""
    agent = request.user.agent_profile
    pw_form = ChangePasswordForm(user=request.user)
    show_pw_modal = False

    if request.method == 'POST':
        if 'change_password' in request.POST:
            pw_form = ChangePasswordForm(user=request.user, data=request.POST)
            if pw_form.is_valid():
                request.user.set_password(pw_form.cleaned_data['new_password1'])
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully.')
                return redirect('agents:profile')
            show_pw_modal = True
            form = AgentProfileForm(instance=agent)
        else:
            form = AgentProfileForm(request.POST, instance=agent)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('agents:profile')
    else:
        form = AgentProfileForm(instance=agent)

    return render(request, 'agents/profile.html', {
        'agent': agent,
        'form': form,
        'pw_form': pw_form,
        'show_pw_modal': show_pw_modal,
    })
