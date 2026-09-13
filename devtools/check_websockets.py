#!/usr/bin/env python
"""
WebSocket access control.

The consumers roll their own token lookup instead of using DRF's
TokenAuthentication, and that copy - duplicated across two consumers - did
not check whether the account was still active. A suspended user kept their
live notification feed and could still join chats using a token issued
before the ban.

    python devtools/check_websockets.py
"""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','worker_connect.settings')
import django; django.setup()
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
setup_test_environment(); runner=DiscoverRunner(verbosity=0,interactive=False); cfg=runner.setup_databases()
from channels.testing.websocket import WebsocketCommunicator
from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token
from accounts.models import User
from worker_connect.asgi import application
ok=fail=0
def check(l,c,d=''):
    global ok,fail
    if c: ok+=1; print(f'  PASS  {l}')
    else: fail+=1; print(f'  FAIL  {l}   [{d}]')

alice = User.objects.create_user(username='ws_alice', email='wa@t.co', password='Pw!23456', user_type='client')
bob = User.objects.create_user(username='ws_bob', email='wb@t.co', password='Pw!23456', user_type='worker')
banned = User.objects.create_user(username='ws_banned', email='wx@t.co', password='Pw!23456', user_type='worker')
ta = Token.objects.create(user=alice).key
tbn = Token.objects.create(user=banned).key
banned.is_active = False; banned.save()

async def try_connect(path, token):
    comm = WebsocketCommunicator(application, f'{path}?token={token}')
    try:
        connected, _ = await comm.connect(timeout=6)
        await comm.disconnect()
        return connected
    except Exception as e:
        try: await comm.disconnect()
        except Exception: pass
        return f'EXC {type(e).__name__}'

async def main():
    r = await try_connect('/ws/notifications/', ta)
    check('a valid token connects to notifications', r is True, str(r))
    r = await try_connect('/ws/notifications/', 'garbage-token')
    check('an invalid token is refused', r is not True, str(r))
    r = await try_connect('/ws/notifications/', '')
    check('no token is refused', r is not True, str(r))
    r = await try_connect('/ws/notifications/', tbn)
    check('a DISABLED account is refused', r is not True, f'connected={r}')
    r = await try_connect(f'/ws/chat/{bob.id}/', ta)
    check('chat with no prior message is refused', r is not True, str(r))

asyncio.run(main())
print(f'\n  {ok} passed, {fail} failed\n')
runner.teardown_databases(cfg)
raise SystemExit(1 if fail else 0)
