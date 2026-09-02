#!/usr/bin/env python
"""
Walk each role through the journey they actually perform.

The unit tests and the per-endpoint checks both pass while the product is
broken end to end, because the bugs in this codebase live in the seams: a
booking counted twice because two code paths both maintain the same total,
a worker accepted through the endpoint that forgot to mark them busy. This
follows one job from quote to payout and asserts the state after each step.

    python devtools/check_roles.py
"""
import os, sys, json, decimal, traceback
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
from workers.models import WorkerProfile, WorkerDocument, Category as WCat
from agents.models import AgentProfile
from jobs.models import Category
from jobs.service_request_models import ServiceRequest, ServiceRequestAssignment, TimeTracking
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
D = decimal.Decimal

results = []
def step(role, what, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f'{type(e).__name__}: {e}'
    results.append((role, what, ok, detail))
    print(f'  {"ok  " if ok else "FAIL"} [{role:6}] {what}" '[:96] + ('' if ok else f'   <- {detail}'[:120]))

cat = Category.objects.create(name='Plumber', daily_rate=D('25000'), service_fee=D('30000'))

# ---------- actors ----------
admin = User.objects.create_user(username='r_admin', email='r_admin@t.co', password='Pw!23456',
                                 user_type='admin', is_staff=True, is_superuser=True)
client = User.objects.create_user(username='r_client', email='r_client@t.co', password='Pw!23456',
                                  user_type='client', first_name='Cli', last_name='Ent',
                                  phone_number='+255700111111')
ClientProfile.objects.create(user=client)
worker = User.objects.create_user(username='r_worker', email='r_worker@t.co', password='Pw!23456',
                                  user_type='worker', first_name='Wor', last_name='Ker')
wp = WorkerProfile.objects.create(user=worker, verification_status='verified',
                                  availability='available', is_public=True, city='Dar')
wp.categories.add(cat)
WorkerDocument.objects.create(worker=wp, document_type='id', title='ID',
                              file=SimpleUploadedFile('id.txt', b'x'))
wp.recalculate_completion()
agent = User.objects.create_user(username='r_agent', email='r_agent@t.co', password='Pw!23456',
                                 user_type='agent')
AgentProfile.objects.create(user=agent)

ac, cc, wc, gc = TC(), TC(), TC(), TC()
ac.force_login(admin); cc.force_login(client); wc.force_login(worker); gc.force_login(agent)

print('\n=== CLIENT ===')
step('client', 'sees a price quote before booking', lambda: (
    (lambda r: (r.status_code == 200 and r.json().get('total_price') == 55000.0,
                f'{r.status_code} {r.content[:90]}'))(
        cc.post('/api/clients/calculate-price/', json.dumps(
            {'category_id': cat.id, 'duration_type': 'daily', 'workers_needed': 1}),
            content_type='application/json'))))
def pay_and_book():
    r = cc.post('/api/v1/client/process-payment/', json.dumps(
        {'amount': 55000.0, 'payment_type': 'mpesa', 'phone_number': '+255123456789'}),
        content_type='application/json')
    ref = r.json().get('transaction_id') or r.json().get('reference')
    r2 = cc.post('/api/v1/client/service-requests/create/', json.dumps({
        'category': cat.id, 'title': 'Leaky tap', 'description': 'fix it',
        'location': 'Dar', 'city': 'Dar', 'workers_needed': 1, 'duration_type': 'daily',
        'preferred_date': str(timezone.now().date()), 'preferred_time': '09:00:00',
        'payment_transaction_id': ref or '', 'payment_method': 'mpesa'}),
        content_type='application/json')
    sr = ServiceRequest.objects.filter(client=client).order_by('-id').first()
    return (sr is not None and sr.payment_status == 'paid' and sr.total_price == D('55000'),
            f'HTTP {r2.status_code} status={getattr(sr,"payment_status",None)} total={getattr(sr,"total_price",None)}')
step('client', 'pays and books a service', pay_and_book)
sr = ServiceRequest.objects.filter(client=client).order_by('-id').first()
step('client', 'sees the booking in their list', lambda: (
    (lambda r: ('Leaky tap' in r.content.decode(), f'HTTP {r.status_code}'))(
        cc.get('/api/v1/clients/requests/'))))
step('client', 'their spend total updated', lambda: (
    (lambda p: (p.total_jobs_posted == 1 and p.total_spent == D('55000'),
                f'jobs={p.total_jobs_posted} spent={p.total_spent}'))(
        ClientProfile.objects.get(user=client))))

print('\n=== ADMIN ===')
step('admin', 'sees the pending request on the dashboard', lambda: (
    (lambda r: (r.status_code == 200, f'HTTP {r.status_code}'))(
        ac.get('/api/v1/admin/service-requests/'))))
step('admin', 'sees available workers to assign', lambda: (
    (lambda r: (r.status_code == 200 and b'r_worker' in r.content or b'Wor' in r.content,
                f'HTTP {r.status_code}'))(ac.get('/api/workers/featured/'))))
def assign():
    from admin_panel.service_request_views import _create_assignment
    a = _create_assignment(sr, wp, admin, 1)
    return (a.worker_payment == D('25000'), f'worker_payment={a.worker_payment}')
step('admin', 'assigns the worker (pay = rate, not the invoice)', assign)
asg = ServiceRequestAssignment.objects.filter(service_request=sr).first()

print('\n=== WORKER ===')
step('worker', 'sees the pending assignment', lambda: (
    (lambda r: ('Leaky tap' in r.content.decode(), f'HTTP {r.status_code}'))(
        wc.get('/api/v1/worker/my-assignments/pending/'))))
step('worker', 'accepts it', lambda: (
    (lambda r: ((lambda a, w: (a.status == 'accepted' and w.availability == 'busy',
                               f'HTTP {r.status_code} status={a.status} avail={w.availability}'))(
        ServiceRequestAssignment.objects.get(pk=asg.pk), WorkerProfile.objects.get(pk=wp.pk))))(
        wc.post(f'/api/v1/worker/my-assignments/{asg.id}/respond/', json.dumps({'accepted': True}),
                content_type='application/json'))))
def clock():
    log = TimeTracking.objects.create(service_request=sr, worker=wp,
                                      clock_in=timezone.now() - timedelta(hours=4))
    log.clock_out_now(notes='done')
    a = ServiceRequestAssignment.objects.get(pk=asg.pk)
    return (D(str(a.total_hours_worked)) == D('4.00'), f'assignment hours={a.total_hours_worked}')
step('worker', 'clocks 4 hours onto their own assignment', clock)
def complete():
    a = ServiceRequestAssignment.objects.get(pk=asg.pk)
    a.mark_completed('all good')
    a.refresh_from_db()
    w = WorkerProfile.objects.get(pk=wp.pk)
    return (a.status == 'completed' and w.total_earnings == D('25000'),
            f'status={a.status} earnings={w.total_earnings}')
step('worker', 'completes and is credited their pay', complete)
step('worker', 'statistics show the work and correct earnings', lambda: (
    (lambda r: ((lambda d: (d.get('total_services') == 1 and D(str(d.get('total_earned') or 0)) == D('25000'),
                            f'{d}'))(r.json() if r.status_code == 200 else {})))(
        wc.get('/api/v1/worker/statistics/'))))
def analytics_ok():
    r = wc.get('/workers/analytics/')
    b = r.content.decode('utf8', 'replace')
    return (r.status_code == 200 and ('25,000' in b or '25000' in b)
            and '55,000' not in b, f'HTTP {r.status_code}')
step('worker', 'analytics shows their pay, not the client invoice', analytics_ok)

print('\n=== AGENT ===')
step('agent', 'can reach their dashboard', lambda: (
    (lambda r: (r.status_code in (200, 302), f'HTTP {r.status_code}'))(gc.get('/agents/'))))
step('agent', 'is refused client-only endpoints', lambda: (
    (lambda r: (r.status_code == 403, f'HTTP {r.status_code}'))(gc.get('/api/clients/jobs/'))))
step('agent', 'is refused admin endpoints', lambda: (
    (lambda r: (r.status_code == 403, f'HTTP {r.status_code}'))(
        gc.get('/api/v1/admin/service-requests/'))))

print('\n=== CROSS-ROLE ===')
step('cross', 'worker refused client endpoints', lambda: (
    (lambda r: (r.status_code == 403, f'HTTP {r.status_code}'))(wc.get('/api/clients/jobs/'))))
step('cross', 'client refused worker endpoints', lambda: (
    (lambda r: (r.status_code == 403, f'HTTP {r.status_code}'))(cc.get('/api/v1/worker/statistics/'))))
step('cross', 'anonymous gets no client phone from search', lambda: (
    (lambda r: (client.phone_number not in r.content.decode(), 'phone leaked'))(
        TC().get('/api/search/jobs/'))))

bad = [r for r in results if not r[2]]
print(f'\n  {len(results)-len(bad)} passed, {len(bad)} failed\n')
for role, what, _, detail in bad:
    print(f'    [{role}] {what}\n        {detail}')
runner.teardown_databases(cfg)
raise SystemExit(1 if bad else 0)
