"""
Direct Logic Test - Bypassing HTTP Layer
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from decimal import Decimal
from jobs.service_request_models import ServiceRequest
from workers.models import Category
from accounts.models import User
from django.utils import timezone

print("=" * 70)
print("DIRECT LOGIC TEST - CREATING SERVICE REQUESTS")
print("=" * 70)

category = Category.objects.filter(is_active=True).first()
client = User.objects.filter(user_type='client').first()

if not category or not client:
    print("⚠ Missing test data")
    exit(1)

print(f"\nUsing:")
print(f"  Category: {category.name}")
print(f"  Daily Rate: TSH {category.daily_rate}")
print(f"  Client: {client.email}")

# Test 1: Create request with 1 worker
print("\n" + "-" * 70)
print("TEST 1: Create request with 1 worker")
print("-" * 70)

sr1 = ServiceRequest.objects.create(
    client=client,
    category=category,
    title="Direct Test - 1 Worker",
    description="Testing 1 worker",
    location="Test Location 1",
    city="Dar es Salaam",
    duration_type='daily',
    duration_days=1,
    workers_needed=1,
    daily_rate=category.daily_rate,
    status='pending',
    urgency='normal'
)

sr1.calculate_total_price()
sr1.save()

expected1 = category.daily_rate * 1 * 1
print(f"Workers: 1, Days: 1, Rate: TSH {category.daily_rate}")
print(f"Expected: TSH {expected1}")
print(f"Actual: TSH {sr1.total_price}")
print(f"Match: {'✓ YES' if sr1.total_price == expected1 else '✗ NO'}")

# Test 2: Create request with 3 workers
print("\n" + "-" * 70)
print("TEST 2: Create request with 3 workers, 2 days")
print("-" * 70)

sr2 = ServiceRequest.objects.create(
    client=client,
    category=category,
    title="Direct Test - 3 Workers",
    description="Testing 3 workers",
    location="Test Location 2",
    city="Dar es Salaam",
    duration_type='daily',
    duration_days=2,
    workers_needed=3,
    daily_rate=category.daily_rate,
    status='pending',
    urgency='normal'
)

sr2.calculate_total_price()
sr2.save()

expected2 = category.daily_rate * 2 * 3
print(f"Workers: 3, Days: 2, Rate: TSH {category.daily_rate}")
print(f"Expected: TSH {expected2}")
print(f"Actual: TSH {sr2.total_price}")
print(f"Match: {'✓ YES' if sr2.total_price == expected2 else '✗ NO'}")

# Test 3: Create request with 10 workers
print("\n" + "-" * 70)
print("TEST 3: Create request with 10 workers, 5 days")
print("-" * 70)

sr3 = ServiceRequest.objects.create(
    client=client,
    category=category,
    title="Direct Test - 10 Workers",
    description="Testing 10 workers",
    location="Test Location 3",
    city="Dar es Salaam",
    duration_type='daily',
    duration_days=5,
    workers_needed=10,
    daily_rate=category.daily_rate,
    status='pending',
    urgency='normal'
)

sr3.calculate_total_price()
sr3.save()

expected3 = category.daily_rate * 5 * 10
print(f"Workers: 10, Days: 5, Rate: TSH {category.daily_rate}")
print(f"Expected: TSH {expected3}")
print(f"Actual: TSH {sr3.total_price}")
print(f"Match: {'✓ YES' if sr3.total_price == expected3 else '✗ NO'}")

# Verify they're all in the database
print("\n" + "=" * 70)
print("VERIFYING DATABASE PERSISTENCE")
print("=" * 70)

test_requests = ServiceRequest.objects.filter(
    title__startswith="Direct Test"
).order_by('-id')[:3]

all_correct = True
for sr in test_requests:
    expected = sr.daily_rate * sr.duration_days * sr.workers_needed
    match = sr.total_price == expected
    status = "✓" if match else "✗"
    
    print(f"\n{status} Request #{sr.id}: {sr.title}")
    print(f"    Workers: {sr.workers_needed}, Days: {sr.duration_days}")
    print(f"    Expected: TSH {expected}, Actual: TSH {sr.total_price}")
    
    if not match:
        all_correct = False

# Delete test data
print("\n" + "-" * 70)
print("Cleaning up test data...")
deleted_count = ServiceRequest.objects.filter(
    title__startswith="Direct Test"
).delete()[0]
print(f"Deleted {deleted_count} test requests")

# Final verdict
print("\n" + "=" * 70)
print("FINAL VERDICT")
print("=" * 70)

if all_correct:
    print("✅ ALL TESTS PASSED!")
    print("✅ Price calculation: CORRECT")
    print("✅ Database operations: WORKING")
    print("✅ Multiple workers feature: FULLY FUNCTIONAL")
    print("\n🎉 100% VERIFIED - READY TO CONTINUE!")
else:
    print("✗ Some tests failed")
    print("⚠ Review the output above")

print("=" * 70)
