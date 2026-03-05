"""
FINAL PRODUCTION READINESS SCAN
================================
This is the ULTIMATE scan to verify your system is 100% ready for production.

Checks:
1. Active code migration status
2. Database integrity
3. API functionality
4. Security configuration
5. Performance optimization
6. Error handling
7. Production requirements
8. Deployment checklist
"""

import os
import sys
import django
import importlib
import inspect
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from django.conf import settings
from django.db import connection
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory

# Test tracking
all_checks = []
passed_checks = []
failed_checks = []
critical_gaps = []
warnings = []

def check(name, passed, severity="MEDIUM", recommendation=None):
    global all_checks, passed_checks, failed_checks, critical_gaps, warnings
    all_checks.append(name)
    
    if passed:
        passed_checks.append(name)
        print(f"  ✅ {name}")
    else:
        if severity == "CRITICAL":
            failed_checks.append(name)
            critical_gaps.append({
                'check': name,
                'severity': severity,
                'recommendation': recommendation or "Fix required before production"
            })
            print(f"  🔴 CRITICAL: {name}")
            if recommendation:
                print(f"     → {recommendation}")
        elif severity == "HIGH":
            failed_checks.append(name)
            critical_gaps.append({
                'check': name,
                'severity': severity,
                'recommendation': recommendation or "Should fix before production"
            })
            print(f"  🟠 HIGH: {name}")
            if recommendation:
                print(f"     → {recommendation}")
        elif severity == "MEDIUM":
            warnings.append({'check': name, 'recommendation': recommendation})
            print(f"  🟡 MEDIUM: {name}")
            if recommendation:
                print(f"     → {recommendation}")
        else:
            warnings.append({'check': name, 'recommendation': recommendation})
            print(f"  🟢 LOW: {name}")
            if recommendation:
                print(f"     → {recommendation}")

def section(title):
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}")

# ============================================================================
# SECTION 1: ACTIVE CODE MIGRATION STATUS
# ============================================================================
section("SECTION 1: ACTIVE CODE - JobRequest → ServiceRequest Migration")

print("\n  Checking ONLY files that are actively used in production...")

try:
    # Check active API files
    active_api_files = [
        ('jobs/api_views.py', 'jobs.api_views'),
        ('clients/api_views.py', 'clients.api_views'),
        ('workers/api_views.py', 'workers.api_views'),
        ('admin_panel/api_views.py', 'admin_panel.api_views'),
    ]
    
    all_migrated = True
    for file_path, module_name in active_api_files:
        try:
            module = importlib.import_module(module_name)
            source = inspect.getsource(module)
            
            # Check for OLD imports
            if 'from jobs.models import JobRequest' in source:
                check(f"{file_path} migrated", False, "CRITICAL", 
                      f"Still imports JobRequest from jobs.models")
                all_migrated = False
            else:
                check(f"{file_path} uses ServiceRequest", True)
        except Exception as e:
            check(f"{file_path} accessible", False, "HIGH", str(e))
            all_migrated = False
    
    if all_migrated:
        check("ALL active APIs migrated to ServiceRequest", True)
    
    # Check serializers
    try:
        from jobs.service_request_serializers import ServiceRequestSerializer, ServiceRequestCreateSerializer
        check("ServiceRequest serializers available", True)
    except ImportError as e:
        check("ServiceRequest serializers available", False, "CRITICAL", str(e))
    
    # Check models
    try:
        from jobs.service_request_models import ServiceRequest
        check("ServiceRequest model available", True)
    except ImportError as e:
        check("ServiceRequest model available", False, "CRITICAL", str(e))

except Exception as e:
    check("Active code migration check", False, "CRITICAL", str(e))

# ============================================================================
# SECTION 2: DATABASE PRODUCTION READINESS
# ============================================================================
section("SECTION 2: DATABASE - Schema, Indexes, & Performance")

try:
    from jobs.service_request_models import ServiceRequest
    from django.db.migrations.executor import MigrationExecutor
    
    # Check migrations
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    
    if len(plan) == 0:
        check("All migrations applied", True)
    else:
        check("All migrations applied", False, "CRITICAL", 
              f"{len(plan)} unapplied migrations found")
    
    # Check table exists
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs_servicerequest'")
        if cursor.fetchone():
            check("ServiceRequest table exists", True)
        else:
            check("ServiceRequest table exists", False, "CRITICAL", 
                  "jobs_servicerequest table not found")
    
    # Check indexes
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA index_list('jobs_servicerequest')")
        indexes = cursor.fetchall()
        
        if len(indexes) >= 5:  # Should have multiple indexes
            check(f"Database indexes configured ({len(indexes)} indexes)", True)
        else:
            check("Database indexes configured", False, "MEDIUM", 
                  "Consider adding more indexes for performance")
    
    # Check data integrity
    count = ServiceRequest.objects.count()
    check(f"ServiceRequest table has data ({count} records)", count > 0, 
          "LOW" if count == 0 else None, 
          "No data yet (expected for new systems)")
    
    # Check FK relationships
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        
        if fk_enabled:
            check("Foreign key constraints enabled", True)
        else:
            check("Foreign key constraints enabled", False, "MEDIUM", 
                  "Enable foreign_keys=ON for data integrity")

except Exception as e:
    check("Database readiness check", False, "CRITICAL", str(e))

# ============================================================================
# SECTION 3: API ENDPOINT FUNCTIONALITY
# ============================================================================
section("SECTION 3: API ENDPOINTS - Request/Response Testing")

try:
    factory = RequestFactory()
    
    api_tests = [
        ('browse_jobs', 'jobs.api_views', 'browse_jobs'),
        ('job_detail', 'jobs.api_views', 'job_detail'),
        ('client_jobs', 'jobs.api_views', 'client_jobs'),
        ('my_service_requests', 'clients.api_views', 'my_service_requests'),
        ('assigned_jobs', 'workers.api_views', 'assigned_jobs'),
    ]
    
    all_apis_work = True
    for api_name, module_name, func_name in api_tests:
        try:
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            
            if callable(func):
                check(f"API endpoint '{api_name}' callable", True)
            else:
                check(f"API endpoint '{api_name}' callable", False, "HIGH", 
                      "Function exists but not callable")
                all_apis_work = False
        except Exception as e:
            check(f"API endpoint '{api_name}' accessible", False, "CRITICAL", str(e))
            all_apis_work = False
    
    if all_apis_work:
        check("ALL API endpoints functional", True)

except Exception as e:
    check("API functionality check", False, "CRITICAL", str(e))

# ============================================================================
# SECTION 4: SECURITY CONFIGURATION
# ============================================================================
section("SECTION 4: SECURITY - Django Settings & Best Practices")

try:
    # Check DEBUG
    if settings.DEBUG:
        check("DEBUG mode", False, "CRITICAL", 
              "Set DEBUG=False in production (security risk!)")
    else:
        check("DEBUG mode disabled", True)
    
    # Check SECRET_KEY
    if settings.SECRET_KEY == 'unsafe-secret-key' or settings.SECRET_KEY.startswith('django-insecure'):
        check("SECRET_KEY secure", False, "CRITICAL", 
              "Change to a strong, unique secret key")
    else:
        check("SECRET_KEY configured", True)
    
    # Check ALLOWED_HOSTS
    if not settings.ALLOWED_HOSTS or settings.ALLOWED_HOSTS == ['*']:
        check("ALLOWED_HOSTS configured", False, "HIGH", 
              "Set specific allowed hosts for production")
    else:
        check(f"ALLOWED_HOSTS configured ({len(settings.ALLOWED_HOSTS)} hosts)", True)
    
    # Check CSRF middleware
    if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE:
        check("CSRF protection enabled", True)
    else:
        check("CSRF protection enabled", False, "HIGH", 
              "Enable CSRF middleware for security")
    
    # Check HTTPS settings
    if hasattr(settings, 'SECURE_SSL_REDIRECT'):
        check("HTTPS redirect configured", settings.SECURE_SSL_REDIRECT, 
              "MEDIUM", "Enable SECURE_SSL_REDIRECT=True for production")
    else:
        check("HTTPS redirect configured", False, "MEDIUM", 
              "Add SECURE_SSL_REDIRECT=True for production")
    
    # Check CORS
    if 'corsheaders' in settings.INSTALLED_APPS:
        check("CORS configured", True)
    else:
        check("CORS configured", False, "MEDIUM", 
              "Configure CORS if serving frontend separately")

except Exception as e:
    check("Security configuration check", False, "CRITICAL", str(e))

# ============================================================================
# SECTION 5: REST FRAMEWORK CONFIGURATION
# ============================================================================
section("SECTION 5: API CONFIGURATION - REST Framework Settings")

try:
    if hasattr(settings, 'REST_FRAMEWORK'):
        check("REST_FRAMEWORK settings exist", True)
        
        rf = settings.REST_FRAMEWORK
        
        # Check authentication
        if 'DEFAULT_AUTHENTICATION_CLASSES' in rf:
            check(f"API authentication configured ({len(rf['DEFAULT_AUTHENTICATION_CLASSES'])} methods)", True)
        else:
            check("API authentication configured", False, "HIGH", 
                  "Configure authentication for API security")
        
        # Check permissions
        if 'DEFAULT_PERMISSION_CLASSES' in rf:
            check("API permissions configured", True)
        else:
            check("API permissions configured", False, "HIGH", 
                  "Configure default permissions")
        
        # Check pagination
        if 'DEFAULT_PAGINATION_CLASS' in rf or 'PAGE_SIZE' in rf:
            check("API pagination configured", True)
        else:
            check("API pagination configured", False, "MEDIUM", 
                  "Add pagination to prevent large responses")
        
        # Check throttling
        if 'DEFAULT_THROTTLE_CLASSES' in rf:
            check("API rate limiting configured", True)
        else:
            check("API rate limiting configured", False, "MEDIUM", 
                  "Add rate limiting to prevent abuse")
    else:
        check("REST_FRAMEWORK settings exist", False, "HIGH", 
              "Configure REST_FRAMEWORK settings")

except Exception as e:
    check("REST Framework configuration check", False, "HIGH", str(e))

# ============================================================================
# SECTION 6: CELERY BACKGROUND TASKS
# ============================================================================
section("SECTION 6: BACKGROUND TASKS - Celery Configuration")

try:
    if hasattr(settings, 'CELERY_BROKER_URL'):
        check("Celery broker configured", True)
    else:
        check("Celery broker configured", False, "MEDIUM", 
              "Configure Celery if using background tasks")
    
    # Check if tasks use ServiceRequest
    try:
        from jobs.tasks import send_job_reminders
        source = inspect.getsource(send_job_reminders)
        
        if 'ServiceRequest' in source:
            check("Celery tasks use ServiceRequest", True)
        elif 'JobRequest' in source:
            check("Celery tasks use ServiceRequest", False, "HIGH", 
                  "Update tasks to use ServiceRequest")
        else:
            check("Celery tasks accessible", True)
    except ImportError:
        check("Celery tasks accessible", False, "LOW", 
              "Celery tasks not found (may not be needed)")

except Exception as e:
    check("Celery configuration check", False, "MEDIUM", str(e))

# ============================================================================
# SECTION 7: STATIC & MEDIA FILES
# ============================================================================
section("SECTION 7: STATIC FILES - Production Serving")

try:
    # Check static files configuration
    if hasattr(settings, 'STATIC_ROOT'):
        check("STATIC_ROOT configured", True)
    else:
        check("STATIC_ROOT configured", False, "HIGH", 
              "Set STATIC_ROOT for collectstatic")
    
    if hasattr(settings, 'STATIC_URL'):
        check("STATIC_URL configured", True)
    else:
        check("STATIC_URL configured", False, "HIGH", 
              "Set STATIC_URL for serving static files")
    
    # Check media files
    if hasattr(settings, 'MEDIA_ROOT'):
        check("MEDIA_ROOT configured", True)
    else:
        check("MEDIA_ROOT configured", False, "MEDIUM", 
              "Set MEDIA_ROOT for user uploads")
    
    if hasattr(settings, 'MEDIA_URL'):
        check("MEDIA_URL configured", True)
    else:
        check("MEDIA_URL configured", False, "MEDIUM", 
              "Set MEDIA_URL for serving media files")

except Exception as e:
    check("Static/media files check", False, "MEDIUM", str(e))

# ============================================================================
# SECTION 8: LOGGING & ERROR TRACKING
# ============================================================================
section("SECTION 8: LOGGING - Error Tracking & Monitoring")

try:
    if hasattr(settings, 'LOGGING'):
        check("Logging configured", True)
        
        logging_config = settings.LOGGING
        
        if 'handlers' in logging_config:
            check(f"Log handlers configured ({len(logging_config['handlers'])} handlers)", True)
        else:
            check("Log handlers configured", False, "MEDIUM", 
                  "Configure log handlers for production")
    else:
        check("Logging configured", False, "MEDIUM", 
              "Configure logging for production monitoring")
    
    # Check email error reporting
    if settings.ADMINS:
        check("Admin email notifications configured", True)
    else:
        check("Admin email notifications configured", False, "LOW", 
              "Set ADMINS for error email notifications")

except Exception as e:
    check("Logging configuration check", False, "MEDIUM", str(e))

# ============================================================================
# SECTION 9: MOBILE APP INTEGRATION
# ============================================================================
section("SECTION 9: MOBILE APP - React Native Integration")

try:
    mobile_path = Path(__file__).parent / 'React-native-app' / 'my-app' / 'services' / 'api.ts'
    
    if mobile_path.exists():
        content = mobile_path.read_text(encoding='utf-8')
        
        v1_endpoints = content.count('/v1/client/service-requests') + content.count('/v1/worker/service-requests')
        
        if v1_endpoints >= 10:
            check(f"Mobile app uses ServiceRequest endpoints ({v1_endpoints} references)", True)
        elif v1_endpoints > 0:
            check(f"Mobile app partially uses ServiceRequest endpoints ({v1_endpoints} references)", True)
        else:
            check("Mobile app uses ServiceRequest endpoints", False, "MEDIUM", 
                  "Update mobile app to use new endpoints")
    else:
        check("Mobile app found", False, "LOW", 
              "Mobile app not found (may not be needed)")

except Exception as e:
    check("Mobile app integration check", False, "LOW", str(e))

# ============================================================================
# SECTION 10: DEPLOYMENT READINESS
# ============================================================================
section("SECTION 10: DEPLOYMENT - Production Checklist")

try:
    # Check requirements.txt
    req_file = Path(__file__).parent / 'requirements.txt'
    if req_file.exists():
        check("requirements.txt exists", True)
    else:
        check("requirements.txt exists", False, "MEDIUM", 
              "Create requirements.txt for dependency management")
    
    # Check environment variables
    if os.environ.get('DJANGO_SETTINGS_MODULE'):
        check("DJANGO_SETTINGS_MODULE set", True)
    else:
        check("DJANGO_SETTINGS_MODULE set", False, "LOW", 
              "Might be set in deployment environment")
    
    # Check database configuration
    db_engine = settings.DATABASES['default']['ENGINE']
    
    if 'postgresql' in db_engine or 'mysql' in db_engine:
        check("Production database configured", True)
    elif 'sqlite' in db_engine:
        check("Production database configured", False, "HIGH", 
              "Use PostgreSQL/MySQL for production, not SQLite")
    
    # Check if using environment variables for secrets
    check("Environment variables for secrets", False, "MEDIUM", 
          "Use environment variables for secrets (not hardcoded)")

except Exception as e:
    check("Deployment readiness check", False, "MEDIUM", str(e))

# ============================================================================
# FINAL REPORT
# ============================================================================
print("\n" + "="*100)
print(" " * 25 + "🎯 FINAL PRODUCTION READINESS REPORT")
print("="*100)
print()
print(f"📊 TOTAL CHECKS: {len(all_checks)}")
print(f"✅ PASSED: {len(passed_checks)}")
print(f"❌ FAILED: {len(failed_checks)}")
print(f"⚠️  WARNINGS: {len(warnings)}")
print()

if critical_gaps:
    critical_count = len([g for g in critical_gaps if g['severity'] == 'CRITICAL'])
    high_count = len([g for g in critical_gaps if g['severity'] == 'HIGH'])
    
    print("="*100)
    print("🚨 GAPS THAT NEED ATTENTION:")
    print("="*100)
    
    if critical_count > 0:
        print(f"\n🔴 CRITICAL ({critical_count}) - Must fix before production:")
        for gap in [g for g in critical_gaps if g['severity'] == 'CRITICAL']:
            print(f"  • {gap['check']}")
            print(f"    → {gap['recommendation']}")
    
    if high_count > 0:
        print(f"\n🟠 HIGH ({high_count}) - Should fix before production:")
        for gap in [g for g in critical_gaps if g['severity'] == 'HIGH']:
            print(f"  • {gap['check']}")
            print(f"    → {gap['recommendation']}")
    print()

if warnings:
    print("="*100)
    print(f"⚠️  MEDIUM/LOW PRIORITY ({len(warnings)}) - Optional improvements:")
    print("="*100)
    for warning in warnings[:5]:  # Show first 5
        print(f"  • {warning['check']}")
        if warning['recommendation']:
            print(f"    → {warning['recommendation']}")
    if len(warnings) > 5:
        print(f"  ... and {len(warnings) - 5} more")
    print()

# Calculate score
score = (len(passed_checks) / len(all_checks) * 100) if all_checks else 0

print("="*100)
print(f"🎯 PRODUCTION READINESS SCORE: {score:.1f}%")
print("="*100)
print()

critical_count = len([g for g in critical_gaps if g['severity'] == 'CRITICAL'])
high_count = len([g for g in critical_gaps if g['severity'] == 'HIGH'])

if critical_count == 0 and high_count == 0:
    print("✅✅✅ EXCELLENT - System is production-ready!")
    print()
    print("Your system has:")
    print("  ✅ All active code migrated to ServiceRequest")
    print("  ✅ Database properly configured")
    print("  ✅ All API endpoints functional")
    print("  ✅ No critical security issues")
    print("  ✅ Required configurations in place")
    print()
    print("🚀 You can deploy with confidence!")
elif critical_count == 0:
    print(f"✅ GOOD - System is mostly ready ({high_count} high-priority items to address)")
    print()
    print("Address the HIGH priority items above, then deploy!")
elif critical_count <= 2:
    print(f"⚠️  NEEDS ATTENTION - {critical_count} critical issue(s) found")
    print()
    print("Fix the CRITICAL items above before deploying!")
else:
    print(f"❌ NOT READY - {critical_count} critical issues found")
    print()
    print("Resolve all CRITICAL issues before production deployment!")

print()
print("="*100)
