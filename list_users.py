#!/usr/bin/env python
"""
List all users in the database for testing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from accounts.models import User

print('=' * 80)
print('ALL USERS FOR TESTING')
print('=' * 80)

users = User.objects.all().order_by('user_type', 'created_at')

if not users.exists():
    print('\n⚠️  No users found in database!')
    print('\nTo create test users, run:')
    print('  python manage.py createsuperuser')
    print('  or register through the web interface')
else:
    for i, user in enumerate(users, 1):
        print(f'\n{i}. {user.get_user_type_display().upper()}')
        print(f'   Email:    {user.email}')
        print(f'   Username: {user.username}')
        print(f'   Name:     {user.first_name} {user.last_name}')
        print(f'   Phone:    {user.phone_number or "N/A"}')
        print(f'   Staff:    {user.is_staff}')
        print(f'   Active:   {user.is_active}')
        print(f'   Created:  {user.created_at.strftime("%Y-%m-%d %H:%M")}')
        
        # Show profile status
        if user.user_type == 'worker' and hasattr(user, 'worker_profile'):
            profile = user.worker_profile
            print(f'   Profile:  {profile.verification_status} | Availability: {profile.availability}')
        elif user.user_type == 'client' and hasattr(user, 'client_profile'):
            profile = user.client_profile
            print(f'   Profile:  Jobs Posted: {profile.total_jobs_posted}')

print(f'\n{"=" * 80}')
print(f'TOTAL USERS: {users.count()}')
print('=' * 80)
print('\n📝 Default Password Hint: If you created these users, use the password you set.')
print('   For testing, consider using a simple password like "test1234" for all test users.\n')
