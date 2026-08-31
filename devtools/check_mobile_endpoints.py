#!/usr/bin/env python
"""
Every endpoint the mobile app calls must exist in the Django URL conf.

The app and the backend are separate codebases that only agree by
convention. A renamed or moved route does not break the build, does not
fail a typecheck, and does not show up in any web test - it just 404s on
someone's phone. This is the cheapest way to catch that before a release.

    python devtools/check_mobile_endpoints.py
"""
import os, re, sys, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
import django; django.setup()
from django.urls import resolve, Resolver404

APP = pathlib.Path(__file__).resolve().parent.parent / 'React-native-app/my-app'
calls = set()
for f in list(APP.rglob('*.ts')) + list(APP.rglob('*.tsx')):
    if 'node_modules' in f.parts: continue
    src = f.read_text(errors='replace')
    for m in re.finditer(r"""\.(get|post|put|patch|delete)\(\s*[`'"]([^`'"]+)""", src):
        calls.add((m.group(1).upper(), m.group(2), f.name))

def normalise(p):
    p = p.split('?')[0]
    p = re.sub(r'\$\{[^}]+\}', '1', p)   # template vars -> a plausible id
    if not p.startswith('/'): return None
    return '/api' + p if not p.startswith('/api') else p

missing, ok = [], 0
for method, raw, where in sorted(calls):
    p = normalise(raw)
    if p is None: continue
    if not p.endswith('/'): p += '/'
    try:
        resolve(p); ok += 1
    except Resolver404:
        missing.append((method, p, raw, where))

print(f'\n  {ok} mobile API calls resolve to a real endpoint')
if missing:
    print(f'  {len(missing)} DO NOT RESOLVE:\n')
    for method, p, raw, where in missing:
        print(f'    {method:6} {p:52} ({where})')
else:
    print('  none missing')
print()
raise SystemExit(1 if missing else 0)
