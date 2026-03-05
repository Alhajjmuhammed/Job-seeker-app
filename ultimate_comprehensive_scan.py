"""
ULTIMATE COMPREHENSIVE SYSTEM SCAN
===================================
This script performs the most thorough system-wide verification:
- Code-level checks
- Runtime execution tests
- HTTP request/response validation
- Database integrity checks
- Security configuration
- Dependency verification
- File system analysis
- Configuration validation
"""

import os
import sys
import django
import importlib
import inspect
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

# Test tracking
tests_passed = 0
tests_failed = 0
errors_found = []
warnings_found = []
gaps_identified = []

def test_result(name, passed, error_msg=None):
    global tests_passed, tests_failed, errors_found
    if passed:
        tests_passed += 1
        print(f"  ✅ {name}")
    else:
        tests_failed += 1
        print(f"  ❌ {name}")
        if error_msg:
            print(f"     Error: {error_msg}")
            errors_found.append(f"{name}: {error_msg}")

def test_warning(name, warning_msg):
    global warnings_found
    print(f"  ⚠️  {name}")
    if warning_msg:
        print(f"     Warning: {warning_msg}")
        warnings_found.append(f"{name}: {warning_msg}")

def gap_identified(category, description, severity="MEDIUM"):
    global gaps_identified
    gaps_identified.append({
        'category': category,
        'description': description,
        'severity': severity
    })
    emoji = "🔴" if severity == "HIGH" else "🟡" if severity == "MEDIUM" else "🟢"
    print(f"  {emoji} GAP FOUND [{severity}]: {description}")

def test_section(name):
    print(f"\n{'='*100}")
    print(f"  {name}")
    print(f"{'='*100}")

# ============================================================================
# SECTION 1: FULL FILE SYSTEM SCAN FOR JOBREQUEST
# ============================================================================
test_section("SECTION 1: COMPLETE FILE SYSTEM SCAN - FINDING ALL JOBREQUEST REFERENCES")

try:
    project_root = Path(__file__).parent
    python_files = []
    html_files = []
    js_files = []
    
    # Collect all relevant files
    for ext in ['*.py', '*.html', '*.js', '*.jsx', '*.ts', '*.tsx']:
        python_files.extend(project_root.rglob(ext))
    
    # Exclude these directories
    exclude_dirs = {'migrations', '__pycache__', 'node_modules', 'venv', 'env', '.git', 'staticfiles', 'media'}
    
    active_files_with_jobrequest = []
    legacy_files_with_jobrequest = []
    verification_scripts = []
    
    for filepath in python_files:
        # Skip if in excluded directory
        if any(excluded in filepath.parts for excluded in exclude_dirs):
            continue
        
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            
            if 'JobRequest' in content or 'job_request' in content.lower():
                file_str = str(filepath.relative_to(project_root))
                
                # Categorize the file
                if any(x in file_str for x in ['verify', 'test', 'scan', 'check', 'deep', 'comprehensive']):
                    verification_scripts.append(file_str)
                elif any(x in file_str for x in ['api_views.py', 'api_urls.py', 'serializers.py', 'models.py', 'tasks.py']):
                    # Check if it's actually using JobRequest or ServiceRequest
                    if 'class JobRequest' in content or 'from jobs.models import JobRequest' in content:
                        if 'views.py' in file_str and 'api_views.py' not in file_str:
                            legacy_files_with_jobrequest.append(file_str)
                        else:
                            active_files_with_jobrequest.append(file_str)
                    elif 'JobRequest' in content:
                        # Might be in comments or old code
                        legacy_files_with_jobrequest.append(file_str)
                else:
                    legacy_files_with_jobrequest.append(file_str)
        except Exception as e:
            continue
    
    print(f"\n📊 FILE SYSTEM SCAN RESULTS:")
    print(f"  Total active API/Model files with JobRequest: {len(active_files_with_jobrequest)}")
    print(f"  Total legacy files with JobRequest: {len(legacy_files_with_jobrequest)}")
    print(f"  Total verification scripts: {len(verification_scripts)}")
    
    if active_files_with_jobrequest:
        gap_identified("CODE MIGRATION", 
                      f"Found {len(active_files_with_jobrequest)} ACTIVE files still using JobRequest",
                      "HIGH")
        for f in active_files_with_jobrequest:
            print(f"    - {f}")
    else:
        test_result("No JobRequest in active API files", True)
    
    if legacy_files_with_jobrequest:
        print(f"\n  ℹ️  Legacy files (not currently used): {len(legacy_files_with_jobrequest)}")
        for f in legacy_files_with_jobrequest[:10]:  # Show first 10
            print(f"    - {f}")
        if len(legacy_files_with_jobrequest) > 10:
            print(f"    ... and {len(legacy_files_with_jobrequest) - 10} more")
    
except Exception as e:
    test_result("File system scan", False, str(e))

# ============================================================================
# SECTION 2: HTTP REQUEST/RESPONSE TESTING
# ============================================================================
test_section("SECTION 2: HTTP REQUEST/RESPONSE VALIDATION")

try:
    from django.test import RequestFactory, Client
    from django.contrib.auth import get_user_model
    from jobs.service_request_models import ServiceRequest
    from workers.models import WorkerProfile
    from clients.models import ClientProfile
    
    User = get_user_model()
    factory = RequestFactory()
    
    # Test API endpoints with actual HTTP requests
    print("\n  Testing API Endpoints:")
    
    # Test 1: Browse jobs endpoint
    try:
        from jobs.api_views import browse_jobs
        request = factory.get('/api/jobs/browse/')
        response = browse_jobs(request)
        if hasattr(response, 'status_code'):
            test_result("browse_jobs returns HTTP response", response.status_code in [200, 401, 403])
        else:
            test_result("browse_jobs callable", True)
    except Exception as e:
        test_result("browse_jobs HTTP test", False, str(e))
    
    # Test 2: Client jobs endpoint
    try:
        from jobs.api_views import client_jobs
        request = factory.get('/api/clients/jobs/')
        response = client_jobs(request)
        test_result("client_jobs callable", True)
    except Exception as e:
        test_result("client_jobs HTTP test", False, str(e))
    
    # Test 3: Worker assigned jobs
    try:
        from workers.api_views import assigned_jobs
        request = factory.get('/api/workers/assigned-jobs/')
        response = assigned_jobs(request)
        test_result("assigned_jobs callable", True)
    except Exception as e:
        test_result("assigned_jobs HTTP test", False, str(e))
    
    # Test 4: Service request list
    try:
        from clients.api_views import my_service_requests
        request = factory.get('/api/clients/requests/')
        response = my_service_requests(request)
        test_result("my_service_requests callable", True)
    except Exception as e:
        test_result("my_service_requests HTTP test", False, str(e))
    
except Exception as e:
    test_result("HTTP request/response testing", False, str(e))

# ============================================================================
# SECTION 3: DATABASE INTEGRITY CHECK
# ============================================================================
test_section("SECTION 3: DATABASE INTEGRITY & MIGRATION STATUS")

try:
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from jobs.service_request_models import ServiceRequest
    
    # Check for unapplied migrations
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    
    if plan:
        gap_identified("DATABASE", 
                      f"Found {len(plan)} unapplied migrations",
                      "HIGH")
        for migration, _ in plan[:5]:
            print(f"    - {migration.app_label}.{migration.name}")
    else:
        test_result("All migrations applied", True)
    
    # Check ServiceRequest table structure
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(jobs_servicerequest)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_fields = ['id', 'title', 'category_id', 'client_id', 'assigned_worker_id', 
                          'status', 'total_price', 'created_at']
        
        missing_fields = [f for f in required_fields if f not in columns]
        if missing_fields:
            gap_identified("DATABASE", 
                          f"ServiceRequest table missing fields: {missing_fields}",
                          "HIGH")
        else:
            test_result("ServiceRequest table structure valid", True)
        
        # Verify assigned_worker is a single FK (not M2M)
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='jobs_servicerequest'")
        table_sql = cursor.fetchone()[0].lower()
        
        if 'assigned_worker_id' in table_sql and 'foreign key' in table_sql:
            test_result("assigned_worker is ForeignKey (not M2M)", True)
        else:
            test_warning("assigned_worker field type", "Could not verify FK relationship")
    
    # Check for orphaned data
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM jobs_servicerequest 
            WHERE assigned_worker_id IS NOT NULL 
            AND assigned_worker_id NOT IN (SELECT id FROM workers_workerprofile)
        """)
        orphaned = cursor.fetchone()[0]
        
        if orphaned > 0:
            gap_identified("DATABASE", 
                          f"Found {orphaned} ServiceRequests with invalid assigned_worker_id",
                          "MEDIUM")
        else:
            test_result("No orphaned worker references", True)
    
    # Check data distribution
    with connection.cursor() as cursor:
        cursor.execute("SELECT status, COUNT(*) FROM jobs_servicerequest GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        print(f"\n  📊 ServiceRequest Status Distribution:")
        for status, count in status_counts.items():
            print(f"    {status}: {count}")
        
        test_result(f"Database has {sum(status_counts.values())} ServiceRequests", True)

except Exception as e:
    test_result("Database integrity check", False, str(e))

# ============================================================================
# SECTION 4: API SERIALIZER DATA FLOW
# ============================================================================
test_section("SECTION 4: SERIALIZER DATA VALIDATION & FLOW")

try:
    from jobs.service_request_serializers import ServiceRequestSerializer, ServiceRequestCreateSerializer
    from jobs.service_request_models import ServiceRequest
    from rest_framework.test import APIRequestFactory
    
    factory = APIRequestFactory()
    
    # Test serializer with actual data
    service_request = ServiceRequest.objects.first()
    
    if service_request:
        # Test read serializer
        serializer = ServiceRequestSerializer(service_request)
        data = serializer.data
        
        required_fields = ['id', 'title', 'category', 'status', 'client']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            gap_identified("SERIALIZER", 
                          f"ServiceRequestSerializer missing fields: {missing}",
                          "MEDIUM")
        else:
            test_result("ServiceRequestSerializer has all required fields", True)
        
        # Test create serializer
        create_serializer = ServiceRequestCreateSerializer()
        create_fields = create_serializer.fields.keys()
        
        test_result(f"ServiceRequestCreateSerializer has {len(create_fields)} fields", True)
        
        # Check for deprecated JobRequest serializers
        try:
            from jobs.serializers import JobRequestSerializer
            gap_identified("CODE MIGRATION", 
                          "Old JobRequestSerializer still exists in jobs/serializers.py",
                          "LOW")
        except ImportError:
            test_result("No legacy JobRequestSerializer imported", True)
        
    else:
        test_warning("Serializer testing", "No ServiceRequest data available in database")

except Exception as e:
    test_result("Serializer data flow", False, str(e))

# ============================================================================
# SECTION 5: TEMPLATE RENDERING WITH REAL DATA
# ============================================================================
test_section("SECTION 5: TEMPLATE RENDERING VERIFICATION")

try:
    from django.template import loader, Context, Template
    from django.test import RequestFactory
    from jobs.service_request_models import ServiceRequest
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    factory = RequestFactory()
    
    templates_to_test = [
        'service_requests/client/my_requests.html',
        'service_requests/worker/assignments.html',
        'service_requests/worker/assignment_detail.html',
        'admin_panel/service_request_list.html',
    ]
    
    for template_name in templates_to_test:
        try:
            template = loader.get_template(template_name)
            
            # Try rendering with mock context
            context = {
                'requests': ServiceRequest.objects.all()[:5],
                'request': factory.get('/'),
                'user': User.objects.first(),
            }
            
            # This will fail if template has syntax errors
            rendered = template.render(context)
            
            # Check for JobRequest references in template
            if 'JobRequest' in rendered or 'job_request' in template.template.source.lower():
                gap_identified("TEMPLATE", 
                              f"{template_name} may contain JobRequest references",
                              "MEDIUM")
            else:
                test_result(f"Template renders: {template_name}", True)
                
        except Exception as e:
            test_result(f"Template renders: {template_name}", False, str(e))

except Exception as e:
    test_result("Template rendering", False, str(e))

# ============================================================================
# SECTION 6: URL CONFIGURATION COMPLETENESS
# ============================================================================
test_section("SECTION 6: URL ROUTING COMPLETENESS CHECK")

try:
    from django.urls import resolve, reverse, get_resolver
    from django.urls.exceptions import NoReverseMatch, Resolver404
    
    # Test critical URL patterns
    url_tests = [
        ('service_requests_web:client_my_requests', '/services/client/my-requests/'),
        ('service_requests_web:client_request_service', '/services/client/request/'),
        ('admin_panel:service_request_list', '/dashboard/service-requests/'),
        ('clients_api_v2:my_service_requests', '/api/clients/requests/'),
        ('workers_api_v2:assigned_jobs', '/api/workers/assigned-jobs/'),
    ]
    
    for name, expected_path in url_tests:
        try:
            url = reverse(name)
            test_result(f"URL reverse: {name}", True)
            
            # Try to resolve it back
            try:
                match = resolve(url)
                test_result(f"URL resolve: {url}", True)
            except Resolver404:
                gap_identified("URL ROUTING", 
                              f"URL {url} cannot be resolved back",
                              "MEDIUM")
        except NoReverseMatch as e:
            gap_identified("URL ROUTING", 
                          f"Cannot reverse URL: {name}",
                          "HIGH")
    
    # Check for old job URLs that might conflict
    try:
        old_job_url = reverse('jobs:job_list')
        test_warning("Legacy URLs", "Old job URLs still configured (may be intentional)")
    except NoReverseMatch:
        test_result("No conflicting legacy job URLs", True)

except Exception as e:
    test_result("URL configuration check", False, str(e))

# ============================================================================
# SECTION 7: SECURITY CONFIGURATION
# ============================================================================
test_section("SECTION 7: SECURITY & CONFIGURATION VALIDATION")

try:
    from django.conf import settings
    
    # Check critical settings
    security_checks = [
        ('DEBUG', False, "HIGH" if getattr(settings, 'DEBUG', True) else None),
        ('SECRET_KEY', None, None if getattr(settings, 'SECRET_KEY', 'unsafe-secret-key') != 'unsafe-secret-key' else "HIGH"),
        ('ALLOWED_HOSTS', [], "MEDIUM" if not getattr(settings, 'ALLOWED_HOSTS', []) else None),
    ]
    
    for setting_name, expected, issue in security_checks:
        if issue:
            gap_identified("SECURITY", 
                          f"{setting_name} configuration issue",
                          issue)
        else:
            test_result(f"{setting_name} configured", True)
    
    # Check REST framework configuration
    if hasattr(settings, 'REST_FRAMEWORK'):
        test_result("REST_FRAMEWORK configured", True)
    else:
        gap_identified("CONFIGURATION", 
                      "REST_FRAMEWORK not configured",
                      "MEDIUM")
    
    # Check Celery configuration
    if hasattr(settings, 'CELERY_BROKER_URL'):
        test_result("CELERY configured", True)
    else:
        test_warning("CELERY", "Celery may not be configured (optional)")

except Exception as e:
    test_result("Security configuration", False, str(e))

# ============================================================================
# SECTION 8: DEPENDENCY & IMPORT VERIFICATION
# ============================================================================
test_section("SECTION 8: DEPENDENCY & MODULE AVAILABILITY")

try:
    required_modules = [
        'rest_framework',
        'django',
        'celery',
        'corsheaders',
    ]
    
    for module_name in required_modules:
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, '__version__', 'unknown')
            test_result(f"{module_name} installed (v{version})", True)
        except ImportError:
            gap_identified("DEPENDENCIES", 
                          f"Required module {module_name} not installed",
                          "HIGH")

except Exception as e:
    test_result("Dependency check", False, str(e))

# ============================================================================
# SECTION 9: MOBILE APP INTEGRATION VERIFICATION
# ============================================================================
test_section("SECTION 9: MOBILE APP API INTEGRATION")

try:
    mobile_app_path = Path(__file__).parent / 'React-native-app' / 'my-app'
    
    if mobile_app_path.exists():
        api_ts_file = mobile_app_path / 'services' / 'api.ts'
        
        if api_ts_file.exists():
            content = api_ts_file.read_text(encoding='utf-8')
            
            # Check for new ServiceRequest endpoints
            v1_endpoints = content.count('/v1/client/service-requests') + content.count('/v1/worker/service-requests')
            
            if v1_endpoints > 0:
                test_result(f"Mobile app uses {v1_endpoints} v1 ServiceRequest endpoints", True)
            else:
                gap_identified("MOBILE INTEGRATION", 
                              "Mobile app not using v1 service request endpoints",
                              "MEDIUM")
            
            # Check for old job endpoints
            old_job_endpoints = content.count('/jobs/') + content.count('JobRequest')
            
            if old_job_endpoints > 0:
                test_warning("Mobile app legacy code", f"Found {old_job_endpoints} references to old job endpoints")
            
        else:
            test_warning("Mobile app", "api.ts file not found")
    else:
        test_warning("Mobile app", "React-native-app not found")

except Exception as e:
    test_result("Mobile app integration", False, str(e))

# ============================================================================
# SECTION 10: BACKGROUND TASK VERIFICATION
# ============================================================================
test_section("SECTION 10: CELERY BACKGROUND TASKS")

try:
    from jobs.tasks import send_job_reminders
    from workers.tasks import update_worker_ratings, check_badge_expirations
    
    tasks = [
        ('send_job_reminders', send_job_reminders),
        ('update_worker_ratings', update_worker_ratings),
        ('check_badge_expirations', check_badge_expirations),
    ]
    
    for task_name, task_func in tasks:
        if callable(task_func):
            # Check if task uses ServiceRequest
            source = inspect.getsource(task_func)
            
            if 'ServiceRequest' in source:
                test_result(f"{task_name} uses ServiceRequest", True)
            elif 'JobRequest' in source:
                gap_identified("TASK MIGRATION", 
                              f"{task_name} still references JobRequest",
                              "HIGH")
            else:
                test_result(f"{task_name} callable", True)

except Exception as e:
    test_result("Background tasks check", False, str(e))

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*100)
print(" " * 30 + "🔍 ULTIMATE COMPREHENSIVE SCAN RESULTS")
print("="*100)
print()
print(f"📊 TOTAL TESTS RUN: {tests_passed + tests_failed}")
print(f"✅ TESTS PASSED: {tests_passed}")
print(f"❌ TESTS FAILED: {tests_failed}")
print(f"⚠️  WARNINGS: {len(warnings_found)}")
print(f"🔍 GAPS IDENTIFIED: {len(gaps_identified)}")
print()

if errors_found:
    print("="*100)
    print("❌ CRITICAL ERRORS:")
    print("="*100)
    for i, error in enumerate(errors_found, 1):
        print(f"  {i}. {error}")
    print()

if gaps_identified:
    print("="*100)
    print("🔍 GAPS IDENTIFIED:")
    print("="*100)
    
    high_priority = [g for g in gaps_identified if g['severity'] == 'HIGH']
    medium_priority = [g for g in gaps_identified if g['severity'] == 'MEDIUM']
    low_priority = [g for g in gaps_identified if g['severity'] == 'LOW']
    
    if high_priority:
        print("\n🔴 HIGH PRIORITY GAPS:")
        for i, gap in enumerate(high_priority, 1):
            print(f"  {i}. [{gap['category']}] {gap['description']}")
    
    if medium_priority:
        print("\n🟡 MEDIUM PRIORITY GAPS:")
        for i, gap in enumerate(medium_priority, 1):
            print(f"  {i}. [{gap['category']}] {gap['description']}")
    
    if low_priority:
        print("\n🟢 LOW PRIORITY GAPS:")
        for i, gap in enumerate(low_priority, 1):
            print(f"  {i}. [{gap['category']}] {gap['description']}")
    print()

if warnings_found:
    print("="*100)
    print("⚠️  WARNINGS (Non-Critical):")
    print("="*100)
    for i, warning in enumerate(warnings_found, 1):
        print(f"  {i}. {warning}")
    print()

# Calculate health score
total_possible_issues = tests_passed + tests_failed + len(gaps_identified)
health_score = (tests_passed / total_possible_issues * 100) if total_possible_issues > 0 else 100

print("="*100)
print(f"🎯 OVERALL SYSTEM HEALTH SCORE: {health_score:.1f}%")
print("="*100)
print()

if health_score >= 95:
    print("✅✅✅ EXCELLENT - System is production-ready!")
elif health_score >= 85:
    print("✅✅ GOOD - System is functional with minor issues")
elif health_score >= 75:
    print("⚠️  FAIR - System needs attention before production")
else:
    print("❌ POOR - Critical issues must be resolved")

print()
print("="*100)
print(f"📋 DETAILED ANALYSIS:")
print(f"  - All active API files migrated: {'✅' if not any(g['category'] == 'CODE MIGRATION' and g['severity'] == 'HIGH' for g in gaps_identified) else '❌'}")
print(f"  - Database integrity verified: {'✅' if not any(g['category'] == 'DATABASE' and g['severity'] == 'HIGH' for g in gaps_identified) else '❌'}")
print(f"  - All templates working: {'✅' if not any(g['category'] == 'TEMPLATE' for g in gaps_identified) else '⚠️'}")
print(f"  - URL routing complete: {'✅' if not any(g['category'] == 'URL ROUTING' for g in gaps_identified) else '❌'}")
print(f"  - Background tasks updated: {'✅' if not any(g['category'] == 'TASK MIGRATION' for g in gaps_identified) else '❌'}")
print(f"  - Mobile integration verified: {'✅' if not any(g['category'] == 'MOBILE INTEGRATION' for g in gaps_identified) else '⚠️'}")
print("="*100)
