"""Find the test worker's username"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from workers.models import WorkerProfile

workers = WorkerProfile.objects.all()
print(f"All Workers ({workers.count()}):")
for w in workers:
    print(f"  ID: {w.id} | Username: {w.user.username} | Name: {w.user.get_full_name()}")
