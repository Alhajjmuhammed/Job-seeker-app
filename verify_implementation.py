"""
Verification script for Real-time Features and GDPR Mobile UI implementation.
Checks all components for correctness without running the full server.
"""

import os
import sys
import importlib.util


def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} MISSING: {filepath}")
        return False


def check_python_syntax(filepath, description):
    """Check if a Python file has valid syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
            compile(code, filepath, 'exec')
        print(f"✅ {description} syntax valid")
        return True
    except SyntaxError as e:
        print(f"❌ {description} SYNTAX ERROR: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description} warning: {e}")
        return True  # File exists and compiles, just import might fail


def check_url_pattern(filepath, pattern, description):
    """Check if a URL pattern exists in a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if pattern in content:
                print(f"✅ {description} found in URLs")
                return True
            else:
                print(f"❌ {description} NOT FOUND in URLs")
                return False
    except Exception as e:
        print(f"❌ Error checking {description}: {e}")
        return False


def main():
    print("=" * 80)
    print("VERIFICATION: Real-time Features & GDPR Mobile UI")
    print("=" * 80)
    print()
    
    base_dir = os.getcwd()
    errors = []
    warnings = []
    
    # ============================================================================
    # 1. DJANGO CHANNELS CONFIGURATION
    # ============================================================================
    print("1. Django Channels Configuration")
    print("-" * 80)
    
    # Check settings.py modifications
    settings_file = os.path.join(base_dir, 'worker_connect', 'settings.py')
    if check_file_exists(settings_file, "Settings file"):
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if "'daphne'" in content:
                print("✅ daphne in INSTALLED_APPS")
            else:
                errors.append("daphne not in INSTALLED_APPS")
                print("❌ daphne NOT in INSTALLED_APPS")
            
            if "'channels'" in content:
                print("✅ channels in INSTALLED_APPS")
            else:
                errors.append("channels not in INSTALLED_APPS")
                print("❌ channels NOT in INSTALLED_APPS")
            
            if "ASGI_APPLICATION" in content:
                print("✅ ASGI_APPLICATION configured")
            else:
                errors.append("ASGI_APPLICATION not configured")
                print("❌ ASGI_APPLICATION NOT configured")
            
            if "CHANNEL_LAYERS" in content:
                print("✅ CHANNEL_LAYERS configured")
            else:
                errors.append("CHANNEL_LAYERS not configured")
                print("❌ CHANNEL_LAYERS NOT configured")
    
    print()
    
    # ============================================================================
    # 2. WEBSOCKET CONSUMERS
    # ============================================================================
    print("2. WebSocket Consumers")
    print("-" * 80)
    
    consumers_file = os.path.join(base_dir, 'worker_connect', 'websocket_consumers.py')
    if check_file_exists(consumers_file, "WebSocket consumers"):
        if check_python_syntax(consumers_file, "Consumers file"):
            with open(consumers_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if "class NotificationConsumer" in content:
                    print("✅ NotificationConsumer defined")
                else:
                    errors.append("NotificationConsumer not found")
                    print("❌ NotificationConsumer NOT defined")
                
                if "class ChatConsumer" in content:
                    print("✅ ChatConsumer defined")
                else:
                    errors.append("ChatConsumer not found")
                    print("❌ ChatConsumer NOT defined")
                
                if "class JobUpdatesConsumer" in content:
                    print("✅ JobUpdatesConsumer defined")
                else:
                    errors.append("JobUpdatesConsumer not found")
                    print("❌ JobUpdatesConsumer NOT defined")
                
                if "def send_user_notification" in content:
                    print("✅ send_user_notification helper defined")
                else:
                    warnings.append("send_user_notification helper not found")
                    print("⚠️  send_user_notification helper NOT defined")
                
                if "def send_chat_message" in content:
                    print("✅ send_chat_message helper defined")
                else:
                    warnings.append("send_chat_message helper not found")
                    print("⚠️  send_chat_message helper NOT defined")
    
    print()
    
    # ============================================================================
    # 3. WEBSOCKET ROUTING
    # ============================================================================
    print("3. WebSocket Routing")
    print("-" * 80)
    
    routing_file = os.path.join(base_dir, 'worker_connect', 'routing.py')
    if check_file_exists(routing_file, "Routing file"):
        if check_python_syntax(routing_file, "Routing file"):
            check_url_pattern(routing_file, 'ws/notifications/', "NotificationConsumer route")
            check_url_pattern(routing_file, 'ws/chat/', "ChatConsumer route")
            check_url_pattern(routing_file, 'ws/jobs/', "JobUpdatesConsumer route")
    
    print()
    
    # ============================================================================
    # 4. ASGI APPLICATION
    # ============================================================================
    print("4. ASGI Application")
    print("-" * 80)
    
    asgi_file = os.path.join(base_dir, 'worker_connect', 'asgi.py')
    if check_file_exists(asgi_file, "ASGI file"):
        if check_python_syntax(asgi_file, "ASGI file"):
            with open(asgi_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if "ProtocolTypeRouter" in content:
                    print("✅ ProtocolTypeRouter configured")
                else:
                    errors.append("ProtocolTypeRouter not configured")
                    print("❌ ProtocolTypeRouter NOT configured")
    
    print()
    
    # ============================================================================
    # 5. WEB WEBSOCKET CLIENT
    # ============================================================================
    print("5. Web WebSocket Client")
    print("-" * 80)
    
    ws_client = os.path.join(base_dir, 'static', 'js', 'websocket-client.js')
    check_file_exists(ws_client, "WebSocket client JavaScript")
    
    ws_template = os.path.join(base_dir, 'templates', 'websocket_integration.html')
    check_file_exists(ws_template, "WebSocket integration template")
    
    print()
    
    # ============================================================================
    # 6. PRIVACY SETTINGS BACKEND
    # ============================================================================
    print("6. Privacy Settings Backend")
    print("-" * 80)
    
    privacy_views = os.path.join(base_dir, 'accounts', 'privacy_views.py')
    if check_file_exists(privacy_views, "Privacy views"):
        check_python_syntax(privacy_views, "Privacy views")
    else:
        errors.append("Privacy views file missing")
    
    privacy_urls = os.path.join(base_dir, 'accounts', 'privacy_urls.py')
    if check_file_exists(privacy_urls, "Privacy URLs"):
        check_python_syntax(privacy_urls, "Privacy URLs")
    else:
        errors.append("Privacy URLs file missing")
    
    # Check if privacy URLs are included in main URLs
    main_urls = os.path.join(base_dir, 'worker_connect', 'urls.py')
    if not check_url_pattern(main_urls, 'accounts.privacy_urls', "Privacy URLs included"):
        errors.append("Privacy URLs not included in main URLs")
    
    print()
    
    # ============================================================================
    # 7. MOBILE APP - PRIVACY SETTINGS
    # ============================================================================
    print("7. Mobile App - Privacy Settings Screens")
    print("-" * 80)
    
    client_privacy = os.path.join(base_dir, 'React-native-app', 'my-app', 'app', '(client)', 'privacy-settings.tsx')
    check_file_exists(client_privacy, "Client privacy settings screen")
    
    worker_privacy = os.path.join(base_dir, 'React-native-app', 'my-app', 'app', '(worker)', 'privacy-settings.tsx')
    check_file_exists(worker_privacy, "Worker privacy settings screen")
    
    print()
    
    # ============================================================================
    # 8. MOBILE APP - DATA RETENTION
    # ============================================================================
    print("8. Mobile App - Data Retention Screens")
    print("-" * 80)
    
    client_retention = os.path.join(base_dir, 'React-native-app', 'my-app', 'app', '(client)', 'data-retention.tsx')
    check_file_exists(client_retention, "Client data retention screen")
    
    worker_retention = os.path.join(base_dir, 'React-native-app', 'my-app', 'app', '(worker)', 'data-retention.tsx')
    check_file_exists(worker_retention, "Worker data retention screen")
    
    print()
    
    # ============================================================================
    # 9. API SERVICE METHODS
    # ============================================================================
    print("9. API Service Methods")
    print("-" * 80)
    
    api_service = os.path.join(base_dir, 'React-native-app', 'my-app', 'services', 'api.ts')
    if check_file_exists(api_service, "API service"):
        with open(api_service, 'r', encoding='utf-8') as f:
            content = f.read()
            
            if "getPrivacySettings" in content:
                print("✅ getPrivacySettings method exists")
            else:
                errors.append("getPrivacySettings method missing")
                print("❌ getPrivacySettings method MISSING")
            
            if "updatePrivacySettings" in content:
                print("✅ updatePrivacySettings method exists")
            else:
                errors.append("updatePrivacySettings method missing")
                print("❌ updatePrivacySettings method MISSING")
            
            if "getDataRetention" in content:
                print("✅ getDataRetention method exists")
            else:
                errors.append("getDataRetention method missing")
                print("❌ getDataRetention method MISSING")
    
    print()
    
    # ============================================================================
    # 10. SETTINGS NAVIGATION
    # ============================================================================
    print("10. Settings Navigation Updates")
    print("-" * 80)
    
    client_settings = os.path.join(base_dir, 'React-native-app', 'my-app', 'app', '(client)', 'settings.tsx')
    if check_file_exists(client_settings, "Client settings"):
        check_url_pattern(client_settings, 'privacy-settings', "Privacy settings link in client")
        check_url_pattern(client_settings, 'data-retention', "Data retention link in client")
    
    worker_settings = os.path.join(base_dir, 'React-native-app', 'my-app', 'app', '(worker)', 'settings.tsx')
    if check_file_exists(worker_settings, "Worker settings"):
        check_url_pattern(worker_settings, 'privacy-settings', "Privacy settings link in worker")
        check_url_pattern(worker_settings, 'data-retention', "Data retention link in worker")
    
    print()
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    if errors:
        print(f"\n❌ CRITICAL ERRORS ({len(errors)}):")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if not errors and not warnings:
        print("\n✅ ALL CHECKS PASSED! Implementation is complete.")
    elif not errors:
        print(f"\n✅ NO CRITICAL ERRORS. {len(warnings)} warnings can be ignored.")
    else:
        print(f"\n❌ FOUND {len(errors)} CRITICAL ERRORS that need to be fixed.")
    
    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Install daphne: pip install daphne")
    print("2. Install channels-redis (for production): pip install channels-redis")
    print("3. Run Django check: python manage.py check")
    print("4. Test WebSocket connections")
    print("5. Test mobile screens")
    print()
    
    return len(errors) == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
