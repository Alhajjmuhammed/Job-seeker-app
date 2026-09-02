#!/usr/bin/env python
"""
The money path, asserted end to end.

A booking used to be marked paid because the caller sent a
payment_transaction_id - any string - so a client could invent a reference
and get the work for free. That was fixed on one of the two booking
endpoints and missed on the other, which left the bypass open on
/api/v1/client/service-requests/create/. The same endpoint also never
passed the category's service_fee, so the platform earned nothing on
anything booked through it.

Both are the same lesson: the money path has more than one implementation,
so it has to be asserted against behaviour, not read.

    python devtools/check_payments.py
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
from clients.models import ClientProfile, PaymentTransaction
from jobs.models import Category
from jobs.service_request_models import ServiceRequest
D = decimal.Decimal
ok=fail=0
def check(l, c, d=''):
    global ok, fail
    if c: ok+=1; print(f'  PASS  {l}')
    else: fail+=1; print(f'  FAIL  {l}   [{d}]')

cat = Category.objects.create(name='Plumber', daily_rate=D('25000'), service_fee=D('30000'))
def mk(name):
    u = User.objects.create_user(username=name, email=f'{name}@t.co', password='Pw!23456', user_type='client')
    ClientProfile.objects.create(user=u)
    c = TC(); c.force_login(u); return u, c
alice, ac = mk('alice')
mallory, mc = mk('mallory')

def issue(client, amount):
    r = client.post('/api/v1/client/process-payment/', json.dumps({
        'amount': float(amount), 'payment_type': 'mpesa', 'phone_number': '+255123456789'}),
        content_type='application/json')
    try: return r.json().get('transaction_id') or r.json().get('reference'), r
    except Exception: return None, r

def book(client, reference, url='/api/v1/client/service-requests/create/'):
    return client.post(url, json.dumps({
        'category': cat.id, 'title': 'Job', 'description': 'd', 'location': 'Dar',
        'city': 'Dar', 'workers_needed': 1, 'duration_type': 'daily',
        'preferred_date': str(timezone.now().date()), 'preferred_time': '09:00:00',
        'payment_transaction_id': reference or '', 'payment_method': 'mpesa',
    }), content_type='application/json')

TOTAL = D('55000')
print()
ref, r = issue(ac, TOTAL)
check('payment endpoint issues a reference', bool(ref), f'HTTP {r.status_code} {r.content[:120]}')

# 1. a genuine reference works
book(ac, ref)
sr = ServiceRequest.objects.filter(client=alice).order_by('-id').first()
check('a genuine reference marks the booking paid',
      sr and sr.payment_status == 'paid' and sr.total_price == TOTAL,
      f'status={getattr(sr,"payment_status",None)} total={getattr(sr,"total_price",None)}')

# 2. the same reference cannot be spent twice
book(ac, ref)
sr2 = ServiceRequest.objects.filter(client=alice).order_by('-id').first()
check('the same reference cannot be spent twice',
      sr2 and sr2.id != sr.id and sr2.payment_status != 'paid',
      f'second booking status={getattr(sr2,"payment_status",None)}')

# 3. another client's reference is refused
ref2, _ = issue(ac, TOTAL)
book(mc, ref2)
srm = ServiceRequest.objects.filter(client=mallory).order_by('-id').first()
check("another client's reference is refused",
      srm and srm.payment_status != 'paid',
      f'status={getattr(srm,"payment_status",None)}')

# 4. a reference for the wrong amount is refused
cheap, _ = issue(ac, D('100'))
book(ac, cheap)
sr4 = ServiceRequest.objects.filter(client=alice).order_by('-id').first()
check('a reference for the wrong amount is refused',
      sr4 and sr4.payment_status != 'paid',
      f'paid a {TOTAL} job with a 100 reference')

# 5. a fabricated reference is refused
book(ac, 'TOTALLY-MADE-UP')
sr5 = ServiceRequest.objects.filter(client=alice).order_by('-id').first()
check('a fabricated reference is refused',
      sr5 and sr5.payment_status != 'paid', 'booked free with an invented reference')

# 6. the service fee is always charged
check('the platform service fee is charged on every booking',
      all(s.total_price == TOTAL for s in ServiceRequest.objects.all()),
      str(sorted({str(s.total_price) for s in ServiceRequest.objects.all()})))

print(f'\n  {ok} passed, {fail} failed\n')
runner.teardown_databases(cfg)
raise SystemExit(1 if fail else 0)
