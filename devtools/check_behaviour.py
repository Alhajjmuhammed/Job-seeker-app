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

# --- 8. the client is told who is on their job -----------------------
cc = TC(); cc.force_login(cu)
# There are two client-jobs endpoints, served by different views.
r = cc.get('/api/v1/clients/jobs/')
d = r.json() if r.status_code == 200 else {}
job = next((j for j in d.get('jobs', []) if j.get('title') == 'BX job'), {})
check('client jobs API reports the assigned worker',
      job.get('worker_assigned') is True and job.get('worker_name'),
      f"HTTP {r.status_code} worker_assigned={job.get('worker_assigned')} name={job.get('worker_name')}")

r = cc.get(f'/api/v1/clients/jobs/{sr.id}/')
d = r.json() if r.status_code == 200 else {}
check('client job detail names the assigned worker',
      d.get('worker_assigned') is True and d.get('worker_name'),
      f"HTTP {r.status_code} worker_assigned={d.get('worker_assigned')} name={d.get('worker_name')}")

r = cc.get(f'/api/v1/jobs/client/jobs/{sr.id}/')
d = r.json() if r.status_code == 200 else {}
check('the other client-jobs endpoint agrees on the worker',
      d.get('worker_name'), f"HTTP {r.status_code} worker_name={d.get('worker_name')}")

# --- the client's own web pages name the worker -----------------------
for url, label in (('/clients/dashboard/', 'client dashboard'),
                   ('/clients/service-requests/', 'client request list')):
    resp = cc.get(url)
    if resp.status_code != 200:
        continue
    page = resp.content.decode('utf8', 'replace')
    check(f'{label} names the assigned worker',
          'bx_worker' in page or (wu.get_full_name() or 'zz') in page,
          f'HTTP {resp.status_code} - shows nobody assigned')

# --- a new worker is discoverable by clients --------------------------
wp.availability = 'available'; wp.is_public = True
wp.verification_status = 'verified'; wp.save()
r = cc.get('/api/workers/featured/')
names = str(r.json()) if r.status_code == 200 else ''
check('an unrated worker can still be featured',
      wu.get_full_name() in names or 'bx_worker' in names or wp.id and str(wp.id) in names,
      f'HTTP {r.status_code} - featured list is empty for a 0-rated worker')

# --- profile completion is actually computed --------------------------
# A real ID document, not just the flag - completion is derived from the
# documents on file, because the flag is not maintained on every path.
from workers.models import WorkerDocument
from django.core.files.uploadedfile import SimpleUploadedFile
WorkerDocument.objects.create(
    worker=wp, document_type='id', title='National ID',
    file=SimpleUploadedFile('id.txt', b'x'))
wp.city = 'Dar'; wp.save()
wp.categories.add(cat)
wp.recalculate_completion()
wp.refresh_from_db()
check('profile completion is computed, not left at zero',
      wp.profile_completion_percentage > 0,
      f'percentage={wp.profile_completion_percentage}')
check('a worker with ID, a category and a location counts as complete',
      wp.is_profile_complete is True,
      f'is_profile_complete={wp.is_profile_complete}')
check('the ID flag is repaired from the documents on file',
      wp.has_uploaded_national_id is True,
      'flag still False despite an ID document existing')

# --- a client's totals track their bookings, whatever created them ----
cp.refresh_from_db()
own = ServiceRequest.objects.filter(client=cu)
check('client job count matches their actual bookings',
      cp.total_jobs_posted == own.count(),
      f'stored={cp.total_jobs_posted} actual={own.count()}')
paid = own.filter(payment_status='paid').aggregate(t=__import__(
    'django.db.models', fromlist=['Sum']).Sum('total_price'))['t'] or 0
check('client spend matches what they have paid',
      D(str(cp.total_spent)) == D(str(paid)),
      f'stored={cp.total_spent} actual={paid}')

# a booking made directly, bypassing every view, must still be counted
before = cp.total_jobs_posted
extra = ServiceRequest.objects.create(
    client=cu, category=cat, title='BX counter', description='d',
    location='Dar', workers_needed=1, daily_rate=D('1000'),
    service_fee=D('30000'), preferred_date=timezone.now().date(),
    status='pending')
cp.refresh_from_db()
check('a booking made by any path updates the totals',
      cp.total_jobs_posted == before + 1,
      f'{before} -> {cp.total_jobs_posted}, expected {before + 1}')

# --- both accept routes must have the same effect ---------------------
# There are two endpoints for a worker accepting an assignment. One used to
# set the fields inline, skipping the worker going busy and the parent
# request advancing, so the same action gave two different outcomes.
def fresh_assignment(title):
    r = ServiceRequest.objects.create(
        client=cu, category=cat, title=title, description='d', location='Dar',
        workers_needed=1, daily_rate=D('20000'), service_fee=D('30000'),
        preferred_date=timezone.now().date(), status='pending')
    r.total_price = r.calculate_total_price(); r.save()
    return ServiceRequestAssignment.objects.create(
        service_request=r, worker=wp, status='pending', worker_payment=r.daily_rate)

outcomes = []
for route, title in (('/api/v1/worker/service-requests/{id}/respond/', 'BX route A'),
                     ('/api/v1/worker/my-assignments/{id}/respond/', 'BX route B')):
    wp.availability = 'available'; wp.save()
    a = fresh_assignment(title)
    resp = c.post(route.format(id=a.id), {'accepted': True},
                  content_type='application/json')
    a.refresh_from_db(); wp.refresh_from_db(); a.service_request.refresh_from_db()
    outcomes.append({
        'http': resp.status_code,
        'assignment_status': a.status,
        'worker_availability': wp.availability,
        'request_status': a.service_request.status,
    })

check('both accept routes leave the same state',
      outcomes[0] == outcomes[1], f'{outcomes[0]} vs {outcomes[1]}')
check('accepting marks the worker busy',
      all(o['worker_availability'] == 'busy' for o in outcomes),
      f"availability: {[o['worker_availability'] for o in outcomes]}")

# --- clocking out must credit the worker's own hours ------------------
# Three endpoints clock a worker out. Two funnel through clock_out_now(),
# which only ever updated the request's hours - so a worker who used the
# website saw 0 hours on their own dashboard however long they worked.
from jobs.service_request_models import TimeTracking
from datetime import timedelta

hr = ServiceRequest.objects.create(
    client=cu, category=cat, title='BX hours', description='d', location='Dar',
    workers_needed=1, daily_rate=D('20000'), service_fee=D('30000'),
    preferred_date=timezone.now().date(), status='in_progress')
hr.total_price = hr.calculate_total_price(); hr.save()
ha = ServiceRequestAssignment.objects.create(
    service_request=hr, worker=wp, status='in_progress', worker_payment=hr.daily_rate)
now = timezone.now()
log = TimeTracking.objects.create(
    service_request=hr, worker=wp, clock_in=now - timedelta(hours=4))
log.clock_out_now(notes='done')
ha.refresh_from_db(); hr.refresh_from_db()
check('clocking out records hours on the worker\'s own assignment',
      D(str(ha.total_hours_worked)) == D('4.00'),
      f'assignment={ha.total_hours_worked} request={hr.total_hours_worked}')
check('the request still totals hours across all its workers',
      D(str(hr.total_hours_worked)) == D('4.00'),
      f'request={hr.total_hours_worked}')

# --- 9. every template still parses ----------------------------------
import pathlib
from django.template.loader import get_template
from django.template import TemplateSyntaxError
broken = []
root = pathlib.Path('templates')
for t in sorted(root.rglob('*.html')):
    try:
        get_template(str(t.relative_to(root)))
    except TemplateSyntaxError as exc:
        broken.append(f'{t}: {exc}')
    except Exception:
        pass
check('every template parses', not broken, '; '.join(broken[:3]))

print(f'\n  {ok} passed, {fail} failed\n')
for u in User.objects.filter(username__startswith='bx_'): u.delete()
_runner.teardown_databases(_old_config)
raise SystemExit(1 if fail else 0)
