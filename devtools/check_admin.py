#!/usr/bin/env python
"""
Admin bulk actions, and what they leave behind.

A bulk action touches many rows at once, so an omission here is multiplied.
Three were found: deleting requests left every worker on them stuck 'busy'
and invisible to the marketplace; deactivating an account still offered
that worker to clients and to the assignment picker; and deleting a worker
left their job reading 'in progress' with nobody doing it. QuerySet.update()
and .delete() never call model methods, which is how each of these was
missed while the single-item paths were correct.

    python devtools/check_admin.py
"""
import os, sys, json, decimal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','worker_connect.settings')
import django; django.setup()
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
setup_test_environment(); runner=DiscoverRunner(verbosity=0,interactive=False); cfg=runner.setup_databases()
from django.test import Client as TC
from django.utils import timezone
from accounts.models import User
from clients.models import ClientProfile
from workers.models import WorkerProfile
from jobs.models import Category
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
D = decimal.Decimal
ok=fail=0
def check(l,c,d=''):
    global ok,fail
    if c: ok+=1; print(f'  PASS  {l}')
    else: fail+=1; print(f'  FAIL  {l}   [{d}]')

cat = Category.objects.create(name='P', daily_rate=D('25000'), service_fee=D('30000'))
admin = User.objects.create_user(username='b_admin', email='ba@t.co', password='Pw!23456',
                                 user_type='admin', is_staff=True, is_superuser=True)
cl = User.objects.create_user(username='b_client', email='bc@t.co', password='Pw!23456', user_type='client')
cp = ClientProfile.objects.create(user=cl)

def make_job(title):
    wu = User.objects.create_user(username=f'w_{title}', email=f'{title}@t.co', password='Pw!23456', user_type='worker')
    wp = WorkerProfile.objects.create(user=wu, verification_status='verified', availability='available')
    sr = ServiceRequest.objects.create(client=cl, category=cat, title=title, description='d',
        location='Dar', workers_needed=1, daily_rate=D('25000'), service_fee=D('30000'),
        preferred_date=timezone.now().date(), status='in_progress')
    sr.total_price = sr.calculate_total_price(); sr.save()
    a = ServiceRequestAssignment.objects.create(service_request=sr, worker=wp,
        status='in_progress', worker_payment=D('25000'))
    wp.availability = 'busy'; wp.save()
    return sr, wp

ac = TC(); ac.force_login(admin)
print()
# bulk CANCEL should release the worker (already fixed)
sr1, wp1 = make_job('cancelme')
ac.post('/api/v1/admin/bulk/jobs/', json.dumps({'job_ids':[sr1.id], 'action':'close'}),
        content_type='application/json')
wp1.refresh_from_db()
check('bulk cancel releases the worker', wp1.availability == 'available', f'availability={wp1.availability}')

# bulk DELETE
sr2, wp2 = make_job('deleteme')
before = cp.total_jobs_posted
r = ac.post('/api/v1/admin/bulk/jobs/', json.dumps({'job_ids':[sr2.id], 'action':'delete'}),
            content_type='application/json')
wp2.refresh_from_db(); cp.refresh_from_db()
check('bulk delete removes the job', not ServiceRequest.objects.filter(id=sr2.id).exists(), f'HTTP {r.status_code}')
check('bulk delete releases the worker', wp2.availability == 'available', f'availability={wp2.availability}')
check('bulk delete updates the client total',
      cp.total_jobs_posted == ServiceRequest.objects.filter(client=cl).count(),
      f'stored={cp.total_jobs_posted} actual={ServiceRequest.objects.filter(client=cl).count()}')


def make_worker(n, assign=False):
    u = User.objects.create_user(username=n, email=f'{n}@t.co', password='Pw!23456', user_type='worker')
    wp = WorkerProfile.objects.create(user=u, verification_status='verified',
                                      availability='available', is_public=True)
    wp.categories.add(cat)
    sr = None
    if assign:
        sr = ServiceRequest.objects.create(client=cl, category=cat, title=f'job_{n}', description='d',
            location='Dar', workers_needed=1, daily_rate=D('25000'), service_fee=D('30000'),
            preferred_date=timezone.now().date(), status='in_progress')
        sr.total_price = sr.calculate_total_price(); sr.save()
        ServiceRequestAssignment.objects.create(service_request=sr, worker=wp,
            status='in_progress', worker_payment=D('25000'))
        wp.availability = 'busy'; wp.save()
    return u, wp, sr

def discoverable(wp):
    return WorkerProfile.objects.filter(id=wp.id, availability='available',
        is_public=True, verification_status='verified').exists()

print()
# 1. deactivating a user must take the worker out of circulation
u1, wp1, _ = make_worker('deact')
ac.post('/api/v1/admin/bulk/users/', json.dumps({'user_ids':[u1.id],'action':'deactivate'}),
        content_type='application/json')
u1.refresh_from_db(); wp1.refresh_from_db()
check('deactivating a user disables the account', not u1.is_active)
check('a deactivated worker is no longer offered to clients',
      not discoverable(wp1), f'still discoverable, availability={wp1.availability}')

# 2. deleting a worker who is on a live job must not strand the job
u2, wp2, sr2 = make_worker('delworker', assign=True)
ac.post('/api/v1/admin/bulk/users/', json.dumps({'user_ids':[u2.id],'action':'delete'}),
        content_type='application/json')
sr2.refresh_from_db()
live = ServiceRequestAssignment.objects.filter(service_request=sr2).exclude(
    status__in=('rejected','cancelled')).count()
check('deleting the only worker does not leave the job "in progress" with nobody',
      not (sr2.status == 'in_progress' and live == 0),
      f'status={sr2.status} live_assignments={live}')

print(f'\n  {ok} passed, {fail} failed\n')
runner.teardown_databases(cfg)
raise SystemExit(1 if fail else 0)
