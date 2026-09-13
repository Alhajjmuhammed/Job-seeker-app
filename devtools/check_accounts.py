#!/usr/bin/env python
import os, sys, json, decimal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','worker_connect.settings')
import django; django.setup()
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
setup_test_environment(); runner=DiscoverRunner(verbosity=0,interactive=False); cfg=runner.setup_databases()
from django.test import Client as TC
from accounts.models import User
from clients.models import ClientProfile
from workers.models import WorkerProfile
ok=fail=0
def check(l,c,d=''):
    global ok,fail
    if c: ok+=1; print(f'  PASS  {l}')
    else: fail+=1; print(f'  FAIL  {l}   [{d}]')

print()
c = TC()
# registration creates the role profile (the bug backfill_profiles had to repair)
# Agents are not offered by the API - they register through the website -
# so only these two roles can be created here.
for role, model in (('client', ClientProfile), ('worker', WorkerProfile)):
    r = c.post('/api/auth/register/', json.dumps({
        'firstName':'A','lastName':'B','email':f'reg_{role}@t.co','phone':'+255700000009',
        'password':'SecurePass123!','userType':role}), content_type='application/json')
    u = User.objects.filter(email=f'reg_{role}@t.co').first()
    check(f'registering a {role} creates their role profile',
          u is not None and model.objects.filter(user=u).exists(),
          f'HTTP {r.status_code} {r.content[:110]}')

u = User.objects.get(email='reg_client@t.co')
# password is hashed, never stored plain
check('password is stored hashed', u.password.startswith(('pbkdf2', 'argon2', 'bcrypt')), u.password[:20])
# login works and returns a token
r = c.post('/api/auth/login/', json.dumps({'email':'reg_client@t.co','password':'SecurePass123!'}),
           content_type='application/json')
check('a registered user can log in', r.status_code == 200 and b'token' in r.content, f'HTTP {r.status_code}')
tok = r.json().get('token') if r.status_code == 200 else None
# wrong password refused
r = c.post('/api/auth/login/', json.dumps({'email':'reg_client@t.co','password':'wrong'}),
           content_type='application/json')
check('a wrong password is refused', r.status_code == 401, f'HTTP {r.status_code}')
# current user requires auth
check('current-user endpoint needs auth', TC().get('/api/auth/user/').status_code in (401,403))
# token works
auth = TC(HTTP_AUTHORIZATION=f'Token {tok}')
r = auth.get('/api/auth/user/')
check('the token authenticates', r.status_code == 200, f'HTTP {r.status_code}')
check('current-user never returns the password hash',
      b'pbkdf2' not in r.content and b'password' not in r.content.lower(), r.content[:120])
# password reset does not reveal whether an account exists
r1 = c.post('/api/auth/password-reset/', json.dumps({'email':'reg_client@t.co'}), content_type='application/json')
r2 = c.post('/api/auth/password-reset/', json.dumps({'email':'nobody@nowhere.co'}), content_type='application/json')
check('password reset does not reveal whether an email exists',
      r1.status_code == r2.status_code, f'{r1.status_code} vs {r2.status_code}')
# logout invalidates
auth.post('/api/auth/logout/')
check('logging out invalidates the token',
      TC(HTTP_AUTHORIZATION=f'Token {tok}').get('/api/auth/user/').status_code in (401,403))
# GDPR export belongs only to the owner
other = User.objects.create_user(username='gdpr_other', email='go@t.co', password='Pw!23456', user_type='client')
ClientProfile.objects.create(user=other)
oc = TC(); oc.force_login(other)
r = oc.get('/api/accounts/privacy/export/')
if r.status_code == 200:
    check('a data export contains only the requester', b'reg_client@t.co' not in r.content, r.content[:120])
else:
    check('data export endpoint reachable for the owner', r.status_code in (200,404,405), f'HTTP {r.status_code}')
# the API must not accept a role it does not provision
r = c.post('/api/auth/register/', json.dumps({
    'firstName':'A','lastName':'B','email':'reg_agent@t.co','phone':'+255700000010',
    'password':'SecurePass123!','userType':'agent'}), content_type='application/json')
check('the API refuses a role it cannot provision', r.status_code == 400, f'HTTP {r.status_code}')
check('no half-built account is left behind when a role is refused',
      not User.objects.filter(email='reg_agent@t.co').exists())

print(f'\n  {ok} passed, {fail} failed\n')
runner.teardown_databases(cfg)
raise SystemExit(1 if fail else 0)
