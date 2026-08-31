#!/usr/bin/env python
"""
Load every parameterless page as every role and fail on a server error.

The static audit checks the template a view names literally. It cannot see
a view that picks its template at runtime, which is how two pages shipped
referring to templates that did not exist - every client and every worker
who opened Direct Hire Requests got a 500, and nothing flagged it.

This renders the pages instead of reading them, which is the only way to
catch that class of break.

    python devtools/smoke_render.py
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','worker_connect.settings'); django.setup()
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
setup_test_environment(); r=DiscoverRunner(verbosity=0,interactive=False); cfg=r.setup_databases()
from django.test import Client as TC
from django.urls import get_resolver
from accounts.models import User
from clients.models import ClientProfile
from workers.models import WorkerProfile
from agents.models import AgentProfile

users = {}
for role, model in (('client', ClientProfile), ('worker', WorkerProfile),
                    ('agent', AgentProfile), ('admin', None)):
    u = User.objects.create_user(username=f'sm_{role}', email=f'sm_{role}@t.co',
                                 password='Pw!23456', user_type=role,
                                 is_staff=(role=='admin'), is_superuser=(role=='admin'))
    if model: model.objects.create(user=u)
    users[role] = u

# every GET-able URL with no parameters
urls = []
def walk(res, prefix=''):
    for p in res.url_patterns:
        pat = prefix + str(p.pattern)
        if hasattr(p, 'url_patterns'): walk(p, pat)
        elif '<' not in pat and '(?P' not in pat: urls.append('/' + pat)
walk(get_resolver())
urls = sorted(set(u for u in urls if not u.startswith('/api') and 'logout' not in u
                  and 'django-admin' not in u and 'delete' not in u and '__' not in u))

broken = []
checked = 0
for role, u in users.items():
    c = TC(); c.force_login(u)
    for url in urls:
        try:
            resp = c.get(url, follow=False)
        except Exception as exc:
            broken.append(f'{role} {url}: {type(exc).__name__}: {str(exc)[:110]}'); continue
        checked += 1
        if resp.status_code >= 500:
            broken.append(f'{role} {url}: HTTP {resp.status_code}')

print(f'\n  rendered {checked} page-loads across {len(users)} roles over {len(urls)} URLs')
if broken:
    print(f'  {len(broken)} BROKEN:')
    for b in broken[:40]: print('   ', b)
else:
    print('  no server errors, no template exceptions')
r.teardown_databases(cfg)
raise SystemExit(1 if broken else 0)
