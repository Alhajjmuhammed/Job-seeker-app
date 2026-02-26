#!/usr/bin/env python
"""
Create test users with known passwords for easy testing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.contrib.auth import get_user_model
from workers.models import WorkerProfile, Category
from clients.models import ClientProfile

User = get_user_model()

def create_test_users():
    print('=' * 80)
    print('CREATING TEST USERS WITH PASSWORD: test1234')
    print('=' * 80)
    
    # Test Admin
    admin, created = User.objects.get_or_create(
        email='admin@test.com',
        defaults={
            'username': 'admin',
            'first_name': 'Admin',
            'last_name': 'User',
            'user_type': 'admin',
            'is_staff': True,
            'is_superuser': True,
            'email_verified': True,
        }
    )
    if created:
        admin.set_password('test1234')
        admin.save()
        print('\n✅ Admin created: admin@test.com / test1234')
    else:
        admin.set_password('test1234')
        admin.save()
        print('\n✅ Admin password reset: admin@test.com / test1234')
    
    # Test Client
    client, created = User.objects.get_or_create(
        email='client@test.com',
        defaults={
            'username': 'client',
            'first_name': 'Test',
            'last_name': 'Client',
            'user_type': 'client',
            'phone_number': '+1234567890',
            'email_verified': True,
        }
    )
    if created:
        client.set_password('test1234')
        client.save()
        ClientProfile.objects.get_or_create(
            user=client,
            defaults={
                'company_name': 'Test Company',
                'city': 'Khartoum',
                'country': 'Sudan'
            }
        )
        print('✅ Client created: client@test.com / test1234')
    else:
        client.set_password('test1234')
        client.save()
        print('✅ Client password reset: client@test.com / test1234')
    
    # Test Worker
    worker, created = User.objects.get_or_create(
        email='worker@test.com',
        defaults={
            'username': 'worker',
            'first_name': 'Test',
            'last_name': 'Worker',
            'user_type': 'worker',
            'phone_number': '+1234567891',
            'email_verified': True,
        }
    )
    if created:
        worker.set_password('test1234')
        worker.save()
        profile, _ = WorkerProfile.objects.get_or_create(
            user=worker,
            defaults={
                'bio': 'Experienced professional worker',
                'city': 'Khartoum',
                'country': 'Sudan',
                'hourly_rate': 50.00,
                'experience_years': 5,
                'availability': 'available',
                'verification_status': 'verified',
            }
        )
        # Add a category if available
        categories = Category.objects.all()[:1]
        if categories:
            profile.categories.add(categories[0])
        print('✅ Worker created: worker@test.com / test1234')
    else:
        worker.set_password('test1234')
        worker.save()
        print('✅ Worker password reset: worker@test.com / test1234')
    
    print('\n' + '=' * 80)
    print('TEST ACCOUNTS READY!')
    print('=' * 80)
    print('\n📋 USE THESE CREDENTIALS:')
    print('\n1. ADMIN LOGIN:')
    print('   Email: admin@test.com')
    print('   Password: test1234')
    print('   Access: http://127.0.0.1:8000/admin/')
    
    print('\n2. CLIENT LOGIN:')
    print('   Email: client@test.com')
    print('   Password: test1234')
    print('   Access: http://127.0.0.1:8000/accounts/login/')
    
    print('\n3. WORKER LOGIN:')
    print('   Email: worker@test.com')
    print('   Password: test1234')
    print('   Access: http://127.0.0.1:8000/accounts/login/')
    
    print('\n' + '=' * 80)

if __name__ == '__main__':
    create_test_users()
