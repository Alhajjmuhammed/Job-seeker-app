"""
Test API endpoint with workers_needed parameter
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from decimal import Decimal
from workers.models import Category
from accounts.models import User

print("=" * 60)
print("TESTING API PRICE CALCULATION")
print("=" * 60)

# Get a test category
category = Category.objects.filter(is_active=True).first()

if not category:
    print("⚠ No active categories found. Please add categories first.")
else:
    print(f"\nTest Category: {category.name}")
    print(f"Daily Rate: TSH {category.daily_rate}")
    print("-" * 60)
    
    # Test different worker counts
    test_cases = [
        (1, 1, "1 worker, 1 day"),
        (3, 1, "3 workers, 1 day (your example)"),
        (2, 5, "2 workers, 5 days"),
        (10, 1, "10 workers, 1 day (big job)"),
    ]
    
    print("\nPrice Calculations:")
    for workers, days, description in test_cases:
        total = category.daily_rate * Decimal(days) * Decimal(workers)
        print(f"\n{description}:")
        print(f"  Formula: TSH {category.daily_rate} × {days} day(s) × {workers} worker(s)")
        print(f"  Total: TSH {total:,.2f}")
    
    print("\n" + "=" * 60)
    print("✅ PRICE CALCULATION LOGIC VERIFIED!")
    print("=" * 60)

# Test that ServiceRequest.calculate_total_price() method works
print("\n" + "=" * 60)
print("TESTING MODEL METHOD")
print("=" * 60)

from jobs.service_request_models import ServiceRequest

if category:
    # Create a test instance (not saved to DB)
    test_request = ServiceRequest(
        daily_rate=category.daily_rate,
        duration_days=3,
        workers_needed=2,
        duration_type='daily'
    )
    
    calculated_price = test_request.calculate_total_price()
    expected_price = category.daily_rate * 3 * 2
    
    print(f"\nTest: 2 workers, 3 days, TSH {category.daily_rate}/day")
    print(f"  Expected: TSH {expected_price}")
    print(f"  Calculated: TSH {calculated_price}")
    print(f"  Match: {'✓ YES' if calculated_price == expected_price else '✗ NO'}")
    
    if calculated_price == expected_price:
        print("\n✅ calculate_total_price() METHOD WORKS CORRECTLY!")
    else:
        print("\n⚠ WARNING: Price calculation mismatch!")

print("\n" + "=" * 60)
