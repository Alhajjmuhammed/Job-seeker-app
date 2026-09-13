#!/usr/bin/env python
"""
Public search: no private data, and no crashing on a mistyped filter.

The worker directory rendered WorkerProfileSerializer - the worker's own
full record - to unauthenticated callers, publishing every worker's email,
phone number, street address, postal code, lifetime earnings and religion.
Religion is special-category data. Separately, numeric filters went
straight into float(), so ?min_rating=abc returned a 500 to anyone who
mistyped a filter or probed one.

    python devtools/check_search.py
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
D = decimal.Decimal
ok=fail=0
def check(l,c,d=''):
    global ok,fail
    if c: ok+=1; print(f'  PASS  {l}')
    else: fail+=1; print(f'  FAIL  {l}   [{d}]')

cat = Category.objects.create(name='P', daily_rate=D('25000'), service_fee=D('30000'))
admin = User.objects.create_user(username='x_admin', email='xa@t.co', password='Pw!23456',
                                 user_type='admin', is_staff=True, is_superuser=True)
cl = User.objects.create_user(username='x_client', email='xc@t.co', password='Pw!23456', user_type='client')
ClientProfile.objects.create(user=cl)
wu = User.objects.create_user(username='x_worker', email='xw@t.co', password='Pw!23456',
                              user_type='worker', phone_number='+255700777666')
wp = WorkerProfile.objects.create(user=wu, verification_status='verified',
                                  availability='available', is_public=True, city='Dar')
wp.categories.add(cat)
ac, cc = TC(), TC(); ac.force_login(admin); cc.force_login(cl)

print('\n  --- SEARCH ---')
# malformed filter values must not 500
for q in ('?min_rating=abc', '?min_rating=-5', '?category=notanumber', '?max_budget=1e999',
          '?q=' + 'A'*5000, "?q=%27%20OR%201%3D1--", '?page=-1', '?page=99999'):
    r = cc.get('/api/v1/search/workers/' + q)
    if r.status_code >= 500:
        check(f'worker search survives {q[:30]}', False, f'HTTP {r.status_code}')
        break
else:
    check('worker search survives malformed filters', True)
for q in ('?min_budget=abc', '?urgency=nonsense', '?page=0'):
    r = cc.get('/api/v1/search/jobs/' + q)
    if r.status_code >= 500:
        check(f'job search survives {q}', False, f'HTTP {r.status_code}'); break
else:
    check('job search survives malformed filters', True)

wu.email = 'private@t.co'; wu.save()
wp.address = '12 Private Lane'; wp.postal_code = '99999'
wp.religion = 'islam'; wp.total_earnings = decimal.Decimal('999999'); wp.save()
LEAKS = {'phone number': '+255700777666', 'email': 'private@t.co',
         'street address': '12 Private Lane', 'postal code': '99999',
         'religion': 'islam', 'lifetime earnings': '999999'}
for url in ('/api/v1/search/workers/', '/api/search/workers/', '/api/jobs/search/workers/'):
    body = TC().get(url).content.decode('utf8', 'replace')
    exposed = [n for n, v in LEAKS.items() if v in body]
    check(f'{url} exposes no worker PII to anonymous callers',
          not exposed, f'exposes: {exposed}')
# and the worker still gets their own full record
own = TC(); own.force_login(wu)
body = own.get('/api/workers/profile/').content.decode('utf8', 'replace')
check('a worker still sees their own contact details',
      'private@t.co' in body or '+255700777666' in body, body[:130])

print('\n  --- BADGES ---')
try:
    from workers.badges import WorkerBadge
    r = cc.get('/api/v1/workers/badges/') if False else None
    check('badge model imports cleanly', True)
except Exception as e:
    check('badge model imports cleanly', False, f'{type(e).__name__}: {e}')

print('\n  --- ADMIN EXPORTS ---')
for path in ('/dashboard/reports/export/csv/', '/dashboard/reports/export/excel/'):
    r = cc.get(path)
    check(f'{path} refuses a non-admin', r.status_code in (302,403,404), f'HTTP {r.status_code}')
    r = ac.get(path)
    check(f'{path} works for an admin', r.status_code == 200, f'HTTP {r.status_code}')
    if r.status_code == 200:
        first = r.content[:400].decode('utf8','replace')
        check(f'{path} is not CSV-injectable',
              not any(line.lstrip().startswith(('=', '+', '-', '@')) for line in first.splitlines() if line),
              first[:100])
print(f'\n  {ok} passed, {fail} failed\n')
runner.teardown_databases(cfg)
raise SystemExit(1 if fail else 0)
