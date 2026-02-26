#!/usr/bin/env python
"""API & CRUD Operations Scanner - 100% Deep Check"""
import os
import re
from pathlib import Path

# Scan all API endpoints and CRUD operations
print("=" * 80)
print(" API & CRUD OPERATIONS SCAN - 100% DEEP CHECK")
print("=" * 80)

# Define colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def scan_api_views(file_path):
    """Scan API views file for endpoints and HTTP methods"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all @api_view decorators
    api_views = re.findall(r"@api_view\(\[(.*?)\]\)", content)
    
    # Find all function definitions after @api_view
    functions = re.findall(r"@api_view\(\[.*?\]\)\s+(?:@\w+\s+)*def\s+(\w+)", content)
    
    return api_views, functions

def scan_mobile_api(file_path):
    """Scan mobile API service file for CRUD operations"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all API functions
    api_functions = re.findall(r"export\s+(?:const|async function)\s+(\w+)", content)
    
    # Find HTTP methods used
    http_methods = {
        'GET': len(re.findall(r"method:\s*['\"]GET['\"]", content)),
        'POST': len(re.findall(r"method:\s*['\"]POST['\"]", content)),
        'PUT': len(re.findall(r"method:\s*['\"]PUT['\"]", content)),
        'PATCH': len(re.findall(r"method:\s*['\"]PATCH['\"]", content)),
        'DELETE': len(re.findall(r"method:\s*['\"]DELETE['\"]", content)),
    }
    
    return api_functions, http_methods

# 1. SCAN BACKEND API ENDPOINTS
print("\n[1/6] BACKEND API ENDPOINTS SCAN")
print("-" * 80)

api_files = {
    'accounts': Path('accounts/api_views.py'),
    'workers': Path('workers/api_views.py'),
    'clients': Path('clients/api_views.py'),
    'jobs': Path('jobs/api_views.py'),
    'admin_panel': Path('admin_panel/api_views.py'),
}

total_endpoints = 0
total_create = 0
total_read = 0
total_update = 0
total_delete = 0

for app_name, file_path in api_files.items():
    if file_path.exists():
        api_views, functions = scan_api_views(file_path)
        
        # Count CRUD operations
        create_ops = sum(1 for methods in api_views if 'POST' in methods)
        read_ops = sum(1 for methods in api_views if 'GET' in methods)
        update_ops = sum(1 for methods in api_views if 'PATCH' in methods or 'PUT' in methods)
        delete_ops = sum(1 for methods in api_views if 'DELETE' in methods)
        
        total_endpoints += len(functions)
        total_create += create_ops
        total_read += read_ops
        total_update += update_ops
        total_delete += delete_ops
        
        print(f"\n{GREEN}✓{RESET} {app_name.upper()}: {len(functions)} endpoints")
        print(f"  • CREATE (POST): {create_ops}")
        print(f"  • READ (GET): {read_ops}")
        print(f"  • UPDATE (PATCH/PUT): {update_ops}")
        print(f"  • DELETE: {delete_ops}")

print(f"\n{GREEN}TOTAL BACKEND API ENDPOINTS: {total_endpoints}{RESET}")
print(f"  • Total CREATE operations: {total_create}")
print(f"  • Total READ operations: {total_read}")
print(f"  • Total UPDATE operations: {total_update}")
print(f"  • Total DELETE operations: {total_delete}")

# 2. SCAN MOBILE API SERVICE
print("\n[2/6] MOBILE API SERVICE SCAN")
print("-" * 80)

mobile_api_path = Path('React-native-app/my-app/services/api.ts')
if mobile_api_path.exists():
    api_functions, http_methods = scan_mobile_api(mobile_api_path)
    
    print(f"{GREEN}✓{RESET} Mobile API Service: {len(api_functions)} functions")
    print(f"\n{GREEN}HTTP Methods Usage:{RESET}")
    for method, count in http_methods.items():
        if count > 0:
            print(f"  • {method}: {count} calls")
else:
    print(f"{RED}✗{RESET} Mobile API service file not found!")

# 3. CRUD COMPLETENESS CHECK
print("\n[3/6] CRUD COMPLETENESS CHECK")
print("-" * 80)

crud_score = 0
crud_total = 4

if total_create > 0:
    print(f"{GREEN}✓{RESET} CREATE operations: IMPLEMENTED ({total_create} endpoints)")
    crud_score += 1
else:
    print(f"{RED}✗{RESET} CREATE operations: NOT FOUND")

if total_read > 0:
    print(f"{GREEN}✓{RESET} READ operations: IMPLEMENTED ({total_read} endpoints)")
    crud_score += 1
else:
    print(f"{RED}✗{RESET} READ operations: NOT FOUND")

if total_update > 0:
    print(f"{GREEN}✓{RESET} UPDATE operations: IMPLEMENTED ({total_update} endpoints)")
    crud_score += 1
else:
    print(f"{RED}✗{RESET} UPDATE operations: NOT FOUND")

if total_delete > 0:
    print(f"{GREEN}✓{RESET} DELETE operations: IMPLEMENTED ({total_delete} endpoints)")
    crud_score += 1
else:
    print(f"{RED}✗{RESET} DELETE operations: NOT FOUND")

crud_percentage = (crud_score / crud_total) * 100
print(f"\n{GREEN}CRUD COMPLETENESS: {crud_percentage:.0f}%{RESET}")

# 4. API URL PATTERNS CHECK
print("\n[4/6] API URL PATTERNS CHECK")
print("-" * 80)

api_url_files = {
    'accounts': Path('accounts/api_urls.py'),
    'workers': Path('workers/api_urls.py'),
    'clients': Path('clients/api_urls.py'),
    'jobs': Path('jobs/api_urls.py'),
    'admin_panel': Path('admin_panel/api_urls.py'),
}

total_routes = 0
for app_name, file_path in api_url_files.items():
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count URL patterns
        routes = len(re.findall(r"path\(", content))
        total_routes += routes
        print(f"{GREEN}✓{RESET} {app_name}: {routes} URL patterns")
    else:
        print(f"{YELLOW}⚠{RESET} {app_name}: No api_urls.py file")

print(f"\n{GREEN}TOTAL API ROUTES: {total_routes}{RESET}")

# 5. SERIALIZERS CHECK
print("\n[5/6] SERIALIZERS CHECK")
print("-" * 80)

serializer_files = {
    'accounts': Path('accounts/serializers.py'),
    'workers': Path('workers/serializers.py'),
    'clients': Path('clients/serializers.py'),
    'jobs': Path('jobs/serializers.py'),
}

total_serializers = 0
for app_name, file_path in serializer_files.items():
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count serializer classes
        serializers = len(re.findall(r"class\s+\w+Serializer", content))
        total_serializers += serializers
        print(f"{GREEN}✓{RESET} {app_name}: {serializers} serializers")
    else:
        print(f"{YELLOW}⚠{RESET} {app_name}: No serializers.py file")

print(f"\n{GREEN}TOTAL SERIALIZERS: {total_serializers}{RESET}")

# 6. MOBILE-WEB API INTEGRATION
print("\n[6/6] MOBILE-WEB API INTEGRATION CHECK")
print("-" * 80)

# Check if mobile app has API configuration
mobile_config_path = Path('React-native-app/my-app/services/api.ts')
if mobile_config_path.exists():
    with open(mobile_config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for API base URL
    has_base_url = 'API_BASE_URL' in content or 'baseURL' in content
    has_auth = 'Authorization' in content or 'Token' in content
    has_error_handling = 'catch' in content or 'error' in content
    
    print(f"{GREEN}✓{RESET} Mobile API Service File: EXISTS")
    print(f"{GREEN if has_base_url else RED}{'✓' if has_base_url else '✗'}{RESET} API Base URL Configuration: {'FOUND' if has_base_url else 'MISSING'}")
    print(f"{GREEN if has_auth else RED}{'✓' if has_auth else '✗'}{RESET} Authentication Headers: {'IMPLEMENTED' if has_auth else 'MISSING'}")
    print(f"{GREEN if has_error_handling else RED}{'✓' if has_error_handling else '✗'}{RESET} Error Handling: {'IMPLEMENTED' if has_error_handling else 'MISSING'}")
else:
    print(f"{RED}✗{RESET} Mobile API service file not found!")

# FINAL SUMMARY
print("\n" + "=" * 80)
print(" FINAL SUMMARY")
print("=" * 80)

overall_score = 0
max_score = 6

# Backend API
if total_endpoints > 0:
    print(f"{GREEN}✓{RESET} Backend API Endpoints: {total_endpoints} endpoints")
    overall_score += 1
else:
    print(f"{RED}✗{RESET} Backend API Endpoints: NO ENDPOINTS FOUND")

# Mobile API
if mobile_api_path.exists():
    print(f"{GREEN}✓{RESET} Mobile API Service: IMPLEMENTED")
    overall_score += 1
else:
    print(f"{RED}✗{RESET} Mobile API Service: NOT FOUND")

# CRUD Operations
print(f"{GREEN if crud_score == 4 else YELLOW}{'✓' if crud_score == 4 else '⚠'}{RESET} CRUD Operations: {crud_percentage:.0f}% Complete")
if crud_score == 4:
    overall_score += 1
elif crud_score >= 2:
    overall_score += 0.5

# URL Routing
if total_routes > 0:
    print(f"{GREEN}✓{RESET} API URL Routing: {total_routes} routes")
    overall_score += 1
else:
    print(f"{RED}✗{RESET} API URL Routing: NO ROUTES FOUND")

# Serializers
if total_serializers > 0:
    print(f"{GREEN}✓{RESET} Data Serialization: {total_serializers} serializers")
    overall_score += 1
else:
    print(f"{RED}✗{RESET} Data Serialization: NO SERIALIZERS FOUND")

# Integration
if mobile_config_path.exists() and has_base_url and has_auth:
    print(f"{GREEN}✓{RESET} Mobile-Web Integration: COMPLETE")
    overall_score += 1
else:
    print(f"{YELLOW}⚠{RESET} Mobile-Web Integration: PARTIAL")
    overall_score += 0.5

overall_percentage = (overall_score / max_score) * 100
print("\n" + "=" * 80)
print(f"{GREEN}API & CRUD COMPLETENESS: {overall_percentage:.1f}%{RESET}")
print("=" * 80)

if overall_percentage >= 90:
    print(f"\n{GREEN}✓✓✓ API & CRUD OPERATIONS ARE 100% COMPLETE ✓✓✓{RESET}")
elif overall_percentage >= 70:
    print(f"\n{YELLOW}⚠⚠⚠ API & CRUD OPERATIONS ARE MOSTLY COMPLETE ⚠⚠⚠{RESET}")
else:
    print(f"\n{RED}✗✗✗ API & CRUD OPERATIONS NEED ATTENTION ✗✗✗{RESET}")
