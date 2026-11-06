"""
Admin home: what needs doing now, and real numbers.

The previous dashboard showed a hard-coded chart (fixed bars for fixed
October dates), percentages typed into the template (+5.8%, -2.1% ...) and
buttons that did nothing. Everything here is counted from the database.
"""
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from agents.models import AgentProfile
from jobs.service_request_models import ServiceRequest
from workers.models import WorkerDocument, WorkerProfile

CHART_DAYS = 14


def _signups_by_day():
    today = timezone.localdate()
    start = today - timedelta(days=CHART_DAYS - 1)
    rows = (User.objects.filter(date_joined__date__gte=start, user_type__in=('worker', 'client'))
            .annotate(day=TruncDate('date_joined')).values('day', 'user_type').annotate(n=Count('id')))
    counts = {(r['day'], r['user_type']): r['n'] for r in rows}
    days = []
    for i in range(CHART_DAYS):
        day = start + timedelta(days=i)
        days.append({'day': day, 'workers': counts.get((day, 'worker'), 0), 'clients': counts.get((day, 'client'), 0)})
    top = max([d['workers'] + d['clients'] for d in days] + [1])
    for d in days:
        d['workers_pct'] = round(d['workers'] * 100 / top)
        d['clients_pct'] = round(d['clients'] * 100 / top)
    return days, sum(d['workers'] for d in days), sum(d['clients'] for d in days)


@staff_member_required
def dashboard(request):
    sr_list = reverse('admin_panel:service_request_list')
    queue = reverse('admin_panel:worker_verification_list')
    no_proof = Q(payment_screenshot='') | Q(payment_screenshot__isnull=True)

    attention = [
        {'label': 'Workers to verify', 'icon': 'bi-person-check', 'url': f'{queue}?status=pending',
         'count': WorkerProfile.objects.filter(verification_status='pending').count()},
        {'label': 'Documents waiting', 'icon': 'bi-file-earmark-check', 'url': f'{queue}?status=all&docs=waiting',
         'count': WorkerDocument.objects.filter(verification_status='pending').count()},
        {'label': 'Payment proofs to check', 'icon': 'bi-cash-coin', 'url': f'{sr_list}?payment=pending',
         'count': ServiceRequest.objects.exclude(no_proof).filter(payment_verified=False)
                  .exclude(status='cancelled').count()},
        {'label': 'Paid, waiting for a worker', 'icon': 'bi-person-plus', 'url': f'{sr_list}?status=pending&payment=verified',
         'count': ServiceRequest.objects.filter(status='pending', payment_verified=True).count()},
        {'label': 'Agents to approve', 'icon': 'bi-person-workspace', 'url': reverse('admin_panel:agent_list') + '?status=pending',
         'count': AgentProfile.objects.filter(is_verified=False).count()},
    ]

    month_start = timezone.localdate().replace(day=1)
    numbers = {
        'verified_workers': WorkerProfile.objects.filter(verification_status='verified', user__is_active=True).count(),
        'workers': User.objects.filter(user_type='worker').count(),
        'clients': User.objects.filter(user_type='client').count(),
        'bookings_month': ServiceRequest.objects.filter(created_at__date__gte=month_start).count(),
        'active_bookings': ServiceRequest.objects.filter(status__in=('assigned', 'in_progress')).count(),
        'completed': ServiceRequest.objects.filter(status='completed').count(),
        'paid_value': ServiceRequest.objects.filter(payment_verified=True).exclude(status='cancelled')
                      .aggregate(total=Sum('total_price'))['total'] or 0,
    }

    days, new_workers, new_clients = _signups_by_day()
    return render(request, 'admin_panel/dashboard.html', {
        'attention': attention,
        'attention_total': sum(a['count'] for a in attention),
        'numbers': numbers,
        'days': days, 'new_workers': new_workers, 'new_clients': new_clients, 'chart_days': CHART_DAYS,
        'recent_workers': WorkerProfile.objects.select_related('user').order_by('-created_at')[:6],
        'recent_bookings': ServiceRequest.objects.select_related('client', 'category').order_by('-created_at')[:6],
    })
