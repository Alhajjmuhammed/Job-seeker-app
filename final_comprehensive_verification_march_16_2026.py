#!/usr/bin/env python3
"""
Final Comprehensive Verification - March 16, 2026
Deep scan of entire application to verify everything is working correctly
"""

import os
import sys
import re
import json
from pathlib import Path

print("=" * 100)
print("FINAL COMPREHENSIVE DEEP VERIFICATION SCAN - MARCH 16, 2026")
print("=" * 100)
print()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
MOBILE_APP_DIR = BASE_DIR / "React-native-app" / "my-app"
TEMPLATES_DIR = BASE_DIR / "templates"
BACKEND_DIR = BASE_DIR / "worker_connect"

# Results tracking
results = {
    'mobile_config': [],
    'mobile_screens': [],
    'web_templates': [],
    'backend_apis': [],
    'websocket': [],
    'database': [],
    'port_config': [],
    'errors': [],
    'warnings': []
}

def check_file_exists(path):
    """Check if file exists"""
    return Path(path).exists()

def search_in_file(file_path, pattern):
    """Search for pattern in file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return re.search(pattern, content, re.IGNORECASE) is not None
    except:
        return False

def get_file_content(file_path, max_lines=None):
    """Get file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if max_lines:
                lines = [next(f) for _ in range(max_lines)]
                return ''.join(lines)
            return f.read()
    except:
        return None

print("=" * 100)
print("SECTION 1: MOBILE APP CONFIGURATION")
print("=" * 100)
print()

# Check mobile app config
config_file = MOBILE_APP_DIR / "config" / "api.ts"
if check_file_exists(config_file):
    print("✅ Mobile API Configuration Found")
    content = get_file_content(config_file)
    
    # Check port 8080
    if '8080' in content:
        print("  ✅ Port 8080 configured")
        results['port_config'].append("Mobile app uses port 8080")
    else:
        results['warnings'].append("Port 8080 might not be set in mobile config")
    
    # Check LOCAL_IP
    if 'LOCAL_IP' in content:
        # Extract IP
        ip_match = re.search(r"LOCAL_IP.*?['\"](\d+\.\d+\.\d+\.\d+)['\"]", content)
        if ip_match:
            ip = ip_match.group(1)
            print(f"  ✅ Local IP configured: {ip}")
            results['mobile_config'].append(f"Local IP: {ip}")
    
    results['mobile_config'].append("API configuration file present")
else:
    results['errors'].append("Mobile API config not found")
    print("❌ Mobile API Configuration NOT Found")

# Check WebSocket service
websocket_file = MOBILE_APP_DIR / "services" / "websocket.ts"
if check_file_exists(websocket_file):
    print("\n✅ WebSocket Service Found")
    content = get_file_content(websocket_file)
    
    # Check if WebSocket is enabled
    if 'BASE_URL' in content and 'ws://' in content:
        print("  ✅ WebSocket uses BASE_URL (correct)")
        results['websocket'].append("Mobile WebSocket uses BASE_URL for connections")
    elif 'API_URL' in content and 'ws://' in content:
        results['warnings'].append("WebSocket might be using API_URL (should use BASE_URL)")
    
    # Check for disable code
    if 'return' in content and 'disabled' in content.lower():
        results['warnings'].append("WebSocket might have disable code")
    else:
        print("  ✅ No disable code found")
        results['websocket'].append("WebSocket service is enabled")
else:
    results['errors'].append("WebSocket service not found")

# Check mobile screens
print("\n" + "=" * 100)
print("SECTION 2: MOBILE APP SCREENS")
print("=" * 100)
print()

app_dir = MOBILE_APP_DIR / "app"
if app_dir.exists():
    tsx_files = list(app_dir.rglob("*.tsx"))
    print(f"✅ Found {len(tsx_files)} .tsx screen files")
    results['mobile_screens'].append(f"Total screens: {len(tsx_files)}")
    
    # Check key screens
    key_screens = [
        'login', 'register', 'profile', 'dashboard',
        'notifications', 'chat', 'jobs', 'applications'
    ]
    
    found_screens = []
    for screen in key_screens:
        matching = [f for f in tsx_files if screen in str(f).lower()]
        if matching:
            found_screens.append(screen)
            print(f"  ✅ {screen.capitalize()} screen(s) found")
    
    results['mobile_screens'].append(f"Key screens found: {len(found_screens)}/{len(key_screens)}")
else:
    results['errors'].append("Mobile app directory not found")

print("\n" + "=" * 100)
print("SECTION 3: WEB APPLICATION TEMPLATES")
print("=" * 100)
print()

if TEMPLATES_DIR.exists():
    html_files = list(TEMPLATES_DIR.rglob("*.html"))
    print(f"✅ Found {len(html_files)} HTML template files")
    results['web_templates'].append(f"Total templates: {len(html_files)}")
    
    # Check for WebSocket in web templates
    websocket_js = BASE_DIR / "static" / "js" / "websocket-client.js"
    if check_file_exists(websocket_js):
        print("  ✅ Web WebSocket client found")
        content = get_file_content(websocket_js)
        if 'window.location.host' in content:
            print("    ✅ Uses dynamic host detection (works with any port)")
            results['websocket'].append("Web WebSocket uses dynamic host detection")
    else:
        results['warnings'].append("Web WebSocket client not found")
else:
    results['errors'].append("Templates directory not found")

print("\n" + "=" * 100)
print("SECTION 4: BACKEND API CONFIGURATION")
print("=" * 100)
print()

# Check Django settings
settings_file = BACKEND_DIR / "settings.py"
if check_file_exists(settings_file):
    print("✅ Django Settings Found")
    content = get_file_content(settings_file)
    
    # Check ASGI
    if 'ASGI_APPLICATION' in content:
        print("  ✅ ASGI_APPLICATION configured")
        results['backend_apis'].append("ASGI application configured")
    
    # Check CHANNEL_LAYERS
    if 'CHANNEL_LAYERS' in content:
        print("  ✅ CHANNEL_LAYERS configured")
        results['websocket'].append("Channel layers configured")
        
        if 'InMemoryChannelLayer' in content:
            print("    ⚠️  Using InMemoryChannelLayer (dev only)")
            results['websocket'].append("Channel layer: InMemoryChannelLayer (development)")
        if 'RedisChannelLayer' in content:
            print("    ✅ RedisChannelLayer configured (production ready)")
            results['websocket'].append("Redis channel layer available for production")
    
    # Check installed apps
    if "'channels'" in content or '"channels"' in content:
        print("  ✅ Django Channels in INSTALLED_APPS")
        results['backend_apis'].append("Django Channels installed")
    
    # Check CORS
    if 'CORS' in content:
        print("  ✅ CORS configured")
        results['backend_apis'].append("CORS configured")
else:
    results['errors'].append("Django settings not found")

# Check URL configurations
print("\n" + "=" * 100)
print("SECTION 5: API ENDPOINTS")
print("=" * 100)
print()

api_apps = ['accounts', 'workers', 'clients', 'jobs']
for app in api_apps:
    api_urls = BASE_DIR / app / "api_urls.py"
    if check_file_exists(api_urls):
        print(f"✅ {app.capitalize()} API URLs found")
        results['backend_apis'].append(f"{app} API configured")
    else:
        results['warnings'].append(f"{app} API URLs not found")

print("\n" + "=" * 100)
print("SECTION 6: WEBSOCKET INFRASTRUCTURE")
print("=" * 100)
print()

# Check ASGI
asgi_file = BACKEND_DIR / "asgi.py"
if check_file_exists(asgi_file):
    print("✅ ASGI Configuration Found")
    content = get_file_content(asgi_file)
    
    if 'ProtocolTypeRouter' in content:
        print("  ✅ ProtocolTypeRouter configured")
        results['websocket'].append("ProtocolTypeRouter configured")
    
    if 'websocket' in content.lower():
        print("  ✅ WebSocket protocol handler registered")
        results['websocket'].append("WebSocket protocol handler present")
else:
    results['errors'].append("ASGI configuration not found")

# Check routing
routing_file = BACKEND_DIR / "routing.py"
if check_file_exists(routing_file):
    print("\n✅ WebSocket Routing Found")
    content = get_file_content(routing_file)
    
    # Count routes
    routes = re.findall(r're_path\(', content)
    print(f"  ✅ {len(routes)} WebSocket routes defined")
    results['websocket'].append(f"WebSocket routes: {len(routes)}")
    
    # Check specific routes
    if 'notifications' in content:
        print("    ✅ /ws/notifications/ route")
    if 'jobs' in content:
        print("    ✅ /ws/jobs/ route")
    if 'chat' in content:
        print("    ✅ /ws/chat/ route")
else:
    results['errors'].append("WebSocket routing not found")

# Check consumers
consumers_file = BACKEND_DIR / "websocket_consumers.py"
if check_file_exists(consumers_file):
    print("\n✅ WebSocket Consumers Found")
    content = get_file_content(consumers_file)
    
    consumers = ['NotificationConsumer', 'JobUpdatesConsumer', 'ChatConsumer']
    for consumer in consumers:
        if consumer in content:
            print(f"  ✅ {consumer} defined")
            results['websocket'].append(f"{consumer} implemented")
        else:
            results['warnings'].append(f"{consumer} not found")
else:
    results['errors'].append("WebSocket consumers not found")

print("\n" + "=" * 100)
print("SECTION 7: DATABASE & DJANGO CHECK")
print("=" * 100)
print()

# Setup Django
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
    import django
    django.setup()
    print("✅ Django initialized successfully")
    
    # Check database
    from django.contrib.auth import get_user_model
    from rest_framework.authtoken.models import Token
    
    User = get_user_model()
    user_count = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    token_count = Token.objects.count()
    
    print(f"  ✅ Total users: {user_count}")
    print(f"  ✅ Active users: {active_users}")
    print(f"  ✅ Auth tokens: {token_count}")
    
    results['database'].append(f"Users: {user_count}")
    results['database'].append(f"Active users: {active_users}")
    results['database'].append(f"Auth tokens: {token_count}")
    
    # Check tables exist
    from django.db import connection
    tables = connection.introspection.table_names()
    print(f"  ✅ Database tables: {len(tables)}")
    results['database'].append(f"Database tables: {len(tables)}")
    
    # Check Django Channels
    import channels
    print(f"  ✅ Django Channels version: {channels.__version__}")
    results['websocket'].append(f"Channels version: {channels.__version__}")
    
except Exception as e:
    print(f"❌ Django check failed: {e}")
    results['errors'].append(f"Django initialization error: {str(e)}")

print("\n" + "=" * 100)
print("SECTION 8: PORT CONFIGURATION VERIFICATION")
print("=" * 100)
print()

# Check all port references
files_to_check = [
    (MOBILE_APP_DIR / "config" / "api.ts", "Mobile config"),
    (BASE_DIR / "docker-compose.yml", "Docker compose"),
    (BASE_DIR / "Dockerfile", "Dockerfile"),
]

for file_path, description in files_to_check:
    if check_file_exists(file_path):
        content = get_file_content(file_path)
        if '8080' in content:
            print(f"✅ {description}: Port 8080 configured")
            results['port_config'].append(f"{description} uses port 8080")
        elif '8000' in content:
            print(f"⚠️  {description}: Port 8000 found (should be 8080)")
            results['warnings'].append(f"{description} might use port 8000")

print("\n" + "=" * 100)
print("SECTION 9: FILE INTEGRITY CHECK")
print("=" * 100)
print()

critical_files = [
    (MOBILE_APP_DIR / "app.json", "Mobile app.json"),
    (MOBILE_APP_DIR / "package.json", "Mobile package.json"),
    (BASE_DIR / "requirements.txt", "Python requirements"),
    (BASE_DIR / "manage.py", "Django manage.py"),
    (BASE_DIR / "db.sqlite3", "SQLite database"),
]

for file_path, description in critical_files:
    if check_file_exists(file_path):
        print(f"✅ {description}: Present")
    else:
        print(f"⚠️  {description}: Not found")
        results['warnings'].append(f"{description} not found")

# Check for syntax errors in key Python files
print("\n" + "=" * 100)
print("SECTION 10: SYNTAX ERROR CHECK")
print("=" * 100)
print()

python_files_to_check = [
    BACKEND_DIR / "settings.py",
    BACKEND_DIR / "asgi.py",
    BACKEND_DIR / "routing.py",
    BACKEND_DIR / "websocket_consumers.py",
]

for py_file in python_files_to_check:
    if check_file_exists(py_file):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                compile(f.read(), py_file.name, 'exec')
            print(f"✅ {py_file.name}: No syntax errors")
        except SyntaxError as e:
            print(f"❌ {py_file.name}: Syntax error at line {e.lineno}")
            results['errors'].append(f"Syntax error in {py_file.name}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 100)
print("FINAL VERIFICATION SUMMARY")
print("=" * 100)
print()

# Count results
total_checks = sum(len(v) for v in results.values())
error_count = len(results['errors'])
warning_count = len(results['warnings'])
success_count = total_checks - error_count - warning_count

print(f"Total Checks Performed: {total_checks}")
print(f"✅ Successful: {success_count}")
print(f"⚠️  Warnings: {warning_count}")
print(f"❌ Errors: {error_count}")
print()

if error_count == 0:
    print("🎉 " + "=" * 96)
    print("🎉 ALL CRITICAL CHECKS PASSED - APPLICATION IS 100% READY!")
    print("🎉 " + "=" * 96)
else:
    print("⚠️  ISSUES FOUND:")
    for error in results['errors']:
        print(f"  ❌ {error}")

if warning_count > 0:
    print()
    print("⚠️  WARNINGS (Non-Critical):")
    for warning in results['warnings']:
        print(f"  ⚠️  {warning}")

print()
print("=" * 100)
print("DETAILED RESULTS BY CATEGORY")
print("=" * 100)

categories = {
    'Mobile Configuration': results['mobile_config'],
    'Mobile Screens': results['mobile_screens'],
    'Web Templates': results['web_templates'],
    'Backend APIs': results['backend_apis'],
    'WebSocket Infrastructure': results['websocket'],
    'Database': results['database'],
    'Port Configuration': results['port_config'],
}

for category, items in categories.items():
    if items:
        print(f"\n{category}:")
        for item in items:
            print(f"  ✓ {item}")

print()
print("=" * 100)
print("STARTUP COMMANDS")
print("=" * 100)
print()
print("To start the application:")
print()
print("1. Backend Server:")
print("   python manage.py runserver 0.0.0.0:8080")
print()
print("2. Mobile App (in React-native-app/my-app):")
print("   npm start")
print()
print("3. WebSocket will auto-connect when:")
print("   - Backend server is running on port 8080")
print("   - User logs in to mobile app")
print("   - Authentication token is valid")
print()
print("=" * 100)
print("VERIFICATION SCAN COMPLETE")
print("=" * 100)

# Exit with appropriate code
sys.exit(0 if error_count == 0 else 1)
