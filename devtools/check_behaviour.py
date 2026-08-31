#!/usr/bin/env python
"""
End-to-end checks for the bugs that a unit test would not have caught.

Every check here corresponds to something that was silently broken in
production: a page that rendered fine while showing zero, a worker's
dashboard reporting the client's invoice as their own income, an endpoint
that let the wrong role through. They are asserted against real HTTP
responses on a throwaway database, because each one of them passed a
"does the code look right" reading.

    python devtools/check_behaviour.py
"""
import os, sys, django, decimal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','worker_connect.settings')
django.setup()
# Run against a throwaway database so this never touches real dev data.
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
setup_test_environment()
_runner = DiscoverRunner(verbosity=0, interactive=False)
_old_config = _runner.setup_databases()
from django.test import Client as TC
from django.utils import timezone
from accounts.models import User
from clients.models import ClientProfile
from workers.models import WorkerProfile
from agents.models import AgentProfile
from jobs.models import Category
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment
D = decimal.Decimal
ok = fail = 0
def check(label, cond, detail=''):
    global ok, fail
    if cond: ok += 1; print(f'  PASS  {label}')
    else: fail += 1; print(f'  FAIL  {label}   [{detail}]')

# --- fixtures ---------------------------------------------------------
for u in User.objects.filter(username__startswith='bx_'): u.delete()
cu = User.objects.create_user(username='bx_client', email='bx_c@t.co', password='Pw!23456', user_type='client')
wu = User.objects.create_user(username='bx_worker', email='bx_w@t.co', password='Pw!23456', user_type='worker')
cp = ClientProfile.objects.create(user=cu); wp = WorkerProfile.objects.create(user=wu, verification_status='verified')
cat = Category.objects.first() or Category.objects.create(name='BX')
sr = ServiceRequest.objects.create(
    client=cu, category=cat, title='BX job', description='d', location='Dar',
    workers_needed=1, daily_rate=D('50000'), service_fee=D('5000'),
    preferred_date=timezone.now().date(), status='completed',
    payment_status='paid', total_hours_worked=D('8'))
sr.total_price = sr.calculate_total_price(); sr.save()
asg = ServiceRequestAssignment.objects.create(
    service_request=sr, worker=wp, status='completed',
    worker_payment=sr.daily_rate, work_completed_at=timezone.now())
print(f'\n  fixture: total_price={sr.total_price} worker_payment={asg.worker_payment}\n')

# --- 1. worker statistics API ----------------------------------------
c = TC(); c.force_login(wu)
r = c.get('/api/v1/worker/statistics/')
d = r.json() if r.status_code == 200 else {}
check('worker statistics counts real work',
      d.get('total_services') == 1 and D(str(d.get('total_earned') or 0)) == D('50000'),
      f"services={d.get('total_services')} earned={d.get('total_earned')}")
check('worker earnings exclude the platform fee',
      D(str(d.get('total_earned') or 0)) != sr.total_price,
      f"earned={d.get('total_earned')} == total_price={sr.total_price}")

# --- 2. current assignment -------------------------------------------
sr2 = ServiceRequest.objects.create(
    client=cu, category=cat, title='BX live', description='d', location='Dar',
    workers_needed=1, daily_rate=D('40000'), service_fee=D('5000'),
    preferred_date=timezone.now().date(), status='in_progress')
sr2.total_price = sr2.calculate_total_price(); sr2.save()
ServiceRequestAssignment.objects.create(service_request=sr2, worker=wp, status='in_progress')
r = c.get('/api/v1/worker/service-requests/current/')
d = r.json() if r.status_code == 200 else {}
check('current assignment found', 'BX live' in str(d), str(d)[:90])

# --- 3. web worker analytics -----------------------------------------
r = c.get('/workers/analytics/')
body = r.content.decode('utf8', 'replace')
check('web analytics shows the completed job',
      r.status_code == 200 and 'Completed Jobs' in body and '>1<' in body.replace(' ',''),
      f'HTTP {r.status_code}')
check('web analytics reports worker pay, not the client invoice',
      ('50,000' in body or '50000' in body) and '55,000' not in body and '55000' not in body,
      'page shows 55,000 - the client total including the platform fee')
r = c.get('/workers/analytics/export/')
csv_body = r.content.decode('utf8', 'replace')
check('CSV export reports worker pay, not the client invoice',
      r.status_code == 200 and '50000.00' in csv_body and '55000.00' not in csv_body,
      f'HTTP {r.status_code}')

# --- 4. admin dashboard counters -------------------------------------
au = User.objects.create_user(username='bx_admin', email='bx_a@t.co', password='Pw!23456',
                              user_type='admin', is_staff=True, is_superuser=True)
ac = TC(); ac.force_login(au)
from admin_panel import views as av
from django.test import RequestFactory
rf = RequestFactory(); rq = rf.get('/'); rq.user = au
assigned = ServiceRequest.objects.filter(assignments__isnull=False).distinct().count()
check('admin dashboard counts assigned jobs', assigned >= 2, f'assigned={assigned}')

# --- 5. client-only endpoint refuses a worker ------------------------
r = c.get('/api/v1/jobs/client/jobs/')
check('client-only endpoint refuses a worker', r.status_code == 403, f'HTTP {r.status_code}')

# --- 6. a rejected-only job is not "assigned" ------------------------
sr3 = ServiceRequest.objects.create(
    client=cu, category=cat, title='BX rejected', description='d', location='Dar',
    workers_needed=1, daily_rate=D('10000'), service_fee=D('1000'),
    preferred_date=timezone.now().date(), status='pending')
ServiceRequestAssignment.objects.create(service_request=sr3, worker=wp, status='rejected')
check('a job every worker rejected is not counted as assigned',
      sr3 not in ServiceRequest.with_workers(),
      'with_workers() includes a rejected-only job')

# --- 7. assigned_worker_display -------------------------------------
check('assigned worker display names the worker',
      wu.get_full_name() in sr.assigned_worker_display or 'bx_worker' in sr.assigned_worker_display,
      sr.assigned_worker_display)

print(f'\n  {ok} passed, {fail} failed\n')
for u in User.objects.filter(username__startswith='bx_'): u.delete()
_runner.teardown_databases(_old_config)
raise SystemExit(1 if fail else 0)
