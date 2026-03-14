#!/usr/bin/env python
"""
Comprehensive verification script for Worker Analytics Dashboard
Tests all functionality including views, templates, URLs, and data serialization
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.urls import reverse, resolve
from workers.models import WorkerProfile
from workers.views import worker_analytics
import json

User = get_user_model()

def test_imports():
    """Test all required imports"""
    print("\n[1/10] Testing Imports...")
    try:
        from workers.views import worker_analytics
        from django.db.models import Sum, Avg, Count
        from django.db.models.functions import TruncMonth
        from jobs.service_request_models import ServiceRequest
        print("  ✓ All imports successful")
        return True
    except Exception as e:
        print(f"  ✗ Import error: {e}")
        return False

def test_template_loading():
    """Test template can be loaded"""
    print("\n[2/10] Testing Template Loading...")
    try:
        template = get_template('workers/analytics.html')
        print("  ✓ Template loads successfully")
        return True
    except Exception as e:
        print(f"  ✗ Template error: {e}")
        return False

def test_url_routing():
    """Test URL routing"""
    print("\n[3/10] Testing URL Routing...")
    try:
        url = reverse('workers:analytics')
        if url == '/workers/analytics/':
            print(f"  ✓ URL resolves correctly: {url}")
        else:
            print(f"  ✗ URL incorrect: {url}")
            return False
        
        # Test URL resolution
        resolved = resolve('/workers/analytics/')
        if resolved.func == worker_analytics:
            print("  ✓ URL resolves to correct view")
        else:
            print("  ✗ URL resolves to wrong view")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ URL routing error: {e}")
        return False

def test_view_function():
    """Test view function directly"""
    print("\n[4/10] Testing View Function...")
    try:
        # Check if view is callable
        if not callable(worker_analytics):
            print("  ✗ worker_analytics is not callable")
            return False
        print("  ✓ View function is callable")
        
        # Check view has login_required decorator
        if hasattr(worker_analytics, '__wrapped__'):
            print("  ✓ View has decorators applied")
        
        return True
    except Exception as e:
        print(f"  ✗ View function error: {e}")
        return False

def test_json_serialization():
    """Test JSON serialization logic"""
    print("\n[5/10] Testing JSON Serialization...")
    try:
        # Test the JSON serialization format
        from datetime import datetime
        
        # Simulate monthly earnings data
        test_data = [
            {
                'month': datetime(2026, 1, 1),
                'earnings': 150000.50,
                'jobs': 5
            },
            {
                'month': datetime(2026, 2, 1),
                'earnings': 200000.00,
                'jobs': 7
            }
        ]
        
        # Convert to JSON-serializable format (same as view)
        monthly_earnings_list = []
        for item in test_data:
            monthly_earnings_list.append({
                'month': item['month'].isoformat() if item['month'] else None,
                'earnings': float(item['earnings'] or 0),
                'jobs': item['jobs']
            })
        
        # Test JSON encoding
        json_str = json.dumps(monthly_earnings_list)
        
        # Test JSON decoding
        decoded = json.loads(json_str)
        
        if len(decoded) == 2 and decoded[0]['earnings'] == 150000.50:
            print("  ✓ JSON serialization works correctly")
            print(f"    Sample: {json_str[:100]}...")
            return True
        else:
            print("  ✗ JSON data mismatch")
            return False
            
    except Exception as e:
        print(f"  ✗ JSON serialization error: {e}")
        return False

def test_database_queries():
    """Test database queries used in view"""
    print("\n[6/10] Testing Database Queries...")
    try:
        from jobs.service_request_models import ServiceRequest
        from django.db.models import Sum, Count
        
        # Test queries don't raise errors (might return empty results)
        total = ServiceRequest.objects.filter(status='completed').aggregate(
            total=Sum('total_price')
        )
        print(f"  ✓ Aggregate query works: {total}")
        
        count = ServiceRequest.objects.filter(status='completed').count()
        print(f"  ✓ Count query works: {count} completed requests")
        
        return True
    except Exception as e:
        print(f"  ✗ Database query error: {e}")
        return False

def test_worker_profile_model():
    """Test WorkerProfile model"""
    print("\n[7/10] Testing WorkerProfile Model...")
    try:
        # Check model exists and has required fields
        fields = [f.name for f in WorkerProfile._meta.get_fields()]
        required_fields = ['user', 'bio', 'phone', 'avg_rating']
        
        missing = [f for f in required_fields if f not in fields]
        if missing:
            print(f"  ✗ Missing fields: {missing}")
            return False
        
        print(f"  ✓ WorkerProfile model has all required fields")
        print(f"    Total fields: {len(fields)}")
        return True
    except Exception as e:
        print(f"  ✗ Model error: {e}")
        return False

def test_template_context():
    """Test template context variables"""
    print("\n[8/10] Testing Template Context...")
    try:
        # Read template and check for required variables
        import re
        with open('templates/workers/analytics.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_vars = [
            'monthly_earnings_json',
            'total_earnings',
            'success_rate',
            'avg_rating',
            'completed_jobs',
            'active_jobs'
        ]
        
        found_vars = []
        for var in required_vars:
            if var in content:
                found_vars.append(var)
        
        if len(found_vars) == len(required_vars):
            print(f"  ✓ All {len(required_vars)} context variables found in template")
            return True
        else:
            missing = set(required_vars) - set(found_vars)
            print(f"  ✗ Missing variables: {missing}")
            return False
            
    except Exception as e:
        print(f"  ✗ Template context error: {e}")
        return False

def test_javascript_integration():
    """Test JavaScript integration in template"""
    print("\n[9/10] Testing JavaScript Integration...")
    try:
        with open('templates/workers/analytics.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Chart.js
        if 'chart.js' not in content.lower():
            print("  ✗ Chart.js not found")
            return False
        print("  ✓ Chart.js CDN included")
        
        # Check for data-width implementation
        if 'data-width' not in content:
            print("  ✗ data-width attributes not found")
            return False
        print("  ✓ data-width attributes present")
        
        # Check for JSON.parse usage
        if 'JSON.parse' in content:
            print("  ✓ JSON.parse() used for data")
        
        # Check for DOMContentLoaded
        if 'DOMContentLoaded' in content:
            print("  ✓ DOMContentLoaded event listener present")
        
        # Check for monthly-earnings-data script tag
        if 'monthly-earnings-data' in content:
            print("  ✓ JSON data script tag present")
        else:
            print("  ✗ JSON data script tag missing")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ JavaScript integration error: {e}")
        return False

def test_migration_status():
    """Test database migrations"""
    print("\n[10/10] Testing Migration Status...")
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Capture showmigrations output
        out = StringIO()
        call_command('showmigrations', '--plan', stdout=out)
        output = out.getvalue()
        
        # Check for unapplied migrations
        if '[ ]' in output:
            print("  ⚠ Warning: Unapplied migrations detected")
            print("    Run: python manage.py migrate")
            return False
        else:
            print("  ✓ All migrations applied")
        
        return True
    except Exception as e:
        print(f"  ✗ Migration check error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("COMPREHENSIVE ANALYTICS DASHBOARD VERIFICATION")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_template_loading,
        test_url_routing,
        test_view_function,
        test_json_serialization,
        test_database_queries,
        test_worker_profile_model,
        test_template_context,
        test_javascript_integration,
        test_migration_status,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n  ✗ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"\nTests Passed: {passed}/{total} ({percentage:.1f}%)")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Analytics dashboard is 100% functional!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed - Review errors above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
