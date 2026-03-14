import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from accounts.gdpr import GDPRService
from django.contrib.auth import get_user_model

User = get_user_model()
test_user = User.objects.filter(user_type='client').first()
data = GDPRService.export_user_data(test_user)

print('\n' + '='*50)
print('GDPR DATA EXPORT - CATEGORIES VERIFICATION')
print('='*50 + '\n')

print('Data categories exported:')
for key in data.keys():
    if isinstance(data[key], list):
        count = len(data[key])
        print(f'  ✅ {key} ({count} items)')
    elif isinstance(data[key], dict):
        count = len(data[key].keys())
        print(f'  ✅ {key} ({count} keys)')
    else:
        print(f'  ✅ {key}')

print(f'\n✅ Total of {len(data.keys())} top-level categories')

print('\n' + '='*50)
print('MATCHING MOBILE UI CATEGORIES')
print('='*50 + '\n')

mobile_categories = {
    'Profile Information': 'account_info' in data or 'profile_info' in data,
    'Service Requests': 'jobs' in data,
    'Messages & Chat': 'messages' in data,
    'Payment Information': 'payments' in data,
    'Reviews & Ratings': 'reviews' in data,
    'Location Data': 'location_history' in data,
    'Usage Analytics': 'usage_analytics' in data,
    'Notifications': 'notifications' in data,
}

for category, present in mobile_categories.items():
    status = '✅' if present else '❌'
    print(f'{status} {category}')

all_present = all(mobile_categories.values())
print(f'\n{"✅ All 8 categories present!" if all_present else "⚠️ Some categories missing"}')
print('='*50 + '\n')
