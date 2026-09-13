#!/usr/bin/env python
"""
GDPR: export what is yours, and nobody else's; anonymise properly.

Anonymisation cleared `profile.phone`, but neither profile model has that
field - the phone lives on User - so the branch never ran and an
"anonymised" account kept its phone number and profile photograph. Both
identify a person at least as well as the name that was being scrubbed.

    python devtools/check_gdpr.py
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
from jobs.models import Category
from jobs.service_request_models import ServiceRequest
D = decimal.Decimal
ok=fail=0
def check(l,c,d=''):
    global ok,fail
    if c: ok+=1; print(f'  PASS  {l}')
    else: fail+=1; print(f'  FAIL  {l}   [{d}]')

cat = Category.objects.create(name='P', daily_rate=D('25000'), service_fee=D('30000'))
alice = User.objects.create_user(username='g_alice', email='ga@t.co', password='Pw!23456',
    user_type='client', first_name='Alice', last_name='Secret', phone_number='+255700999888')
ClientProfile.objects.create(user=alice)
eve = User.objects.create_user(username='g_eve', email='ge@t.co', password='Pw!23456', user_type='client')
ClientProfile.objects.create(user=eve)
sr = ServiceRequest.objects.create(client=alice, category=cat, title='Alice job',
    description='d', location='Dar', workers_needed=1, daily_rate=D('25000'),
    service_fee=D('30000'), preferred_date=timezone.now().date(), status='pending',
    client_notes='ALICE PRIVATE NOTE')
sr.total_price = sr.calculate_total_price(); sr.save()

ac, ec = TC(), TC(); ac.force_login(alice); ec.force_login(eve)
print()
r = ac.get('/api/v1/gdpr/export/')
body = r.content.decode('utf8','replace')
check('a user can export their own data', r.status_code == 200, f'HTTP {r.status_code}')
check('the export contains their own data', 'ALICE PRIVATE NOTE' in body or 'Alice job' in body, body[:140])

r = ec.get('/api/v1/gdpr/export/')
body = r.content.decode('utf8','replace')
check('an export never contains another user’s data',
      'ALICE PRIVATE NOTE' not in body and '+255700999888' not in body and 'ga@t.co' not in body,
      body[:160])

check('export requires authentication', TC().get('/api/v1/gdpr/export/').status_code in (401,403))

r = ac.get('/api/v1/gdpr/delete/preview/')
check('delete preview is available to the owner', r.status_code == 200, f'HTTP {r.status_code}')

# anonymize should scrub identifying data but keep the account row usable
r = ac.post('/api/v1/gdpr/anonymize/', json.dumps({'confirm': True}), content_type='application/json')
alice.refresh_from_db()
if r.status_code in (200, 202):
    check('anonymising removes the real name',
          alice.first_name != 'Alice' or alice.last_name != 'Secret',
          f'still {alice.first_name} {alice.last_name}')
    check('anonymising removes the phone number',
          not alice.phone_number, f'still {alice.phone_number}')
    check('anonymising disables the account', not alice.is_active)
    check('anonymising drops verification flags',
          not alice.email_verified and not alice.phone_verified)
    check('anonymising removes the profile photograph', not alice.profile_picture)
else:
    check('anonymise endpoint responds sensibly', r.status_code in (400,403,405),
          f'HTTP {r.status_code} {r.content[:110]}')
print(f'\n  {ok} passed, {fail} failed\n')
runner.teardown_databases(cfg)
raise SystemExit(1 if fail else 0)
