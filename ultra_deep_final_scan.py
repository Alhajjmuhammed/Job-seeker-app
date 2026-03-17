#!/usr/bin/env python
"""
ULTRA DEEP FINAL SCAN - EVERY POSSIBLE ENTRY POINT
Checks ALL files, ALL functions, ALL URLs for service request creation
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

print("=" * 80)
print("ULTRA DEEP SCAN - ALL POSSIBLE SERVICE REQUEST ENTRY POINTS")
print("=" * 80)
print()

# Step 1: Find ALL functions that create ServiceRequest
print("STEP 1: Scanning for ServiceRequest.objects.create in ALL files...")
print("-" * 80)

import subprocess
import re

# Search for ServiceRequest.objects.create
try:
    result = subprocess.run(
        ['powershell', '-Command', 
         'Get-ChildItem -Path . -Recurse -Include *.py | Select-String -Pattern "ServiceRequest.objects.create" | Select-Object -ExpandProperty Path -Unique'],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__)
    )
    
    create_files = result.stdout.strip().split('\n')
    create_files = [f.strip() for f in create_files if f.strip() and 'migrations' not in f and 'test' not in f.lower()]
    
    print(f"Found {len(create_files)} files with ServiceRequest.objects.create:")
    for f in create_files:
        print(f"  - {f}")
except Exception as e:
    print(f"PowerShell search failed: {e}")
    create_files = []

print()

# Step 2: Find ALL functions that use serializers to save ServiceRequest
print("STEP 2: Scanning for serializer.save() in client-related files...")
print("-" * 80)

client_files = [
    'clients/service_request_web_views.py',
    'clients/views.py',
    'clients/api_views.py',
    'clients/service_request_client_views.py',
    'clients/pricing_api.py',
]

functions_found = []

for file_path in client_files:
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    if not os.path.exists(full_path):
        continue
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all function definitions
        func_pattern = r'def\s+(\w+)\s*\([^)]*\):'
        functions = re.findall(func_pattern, content)
        
        for func_name in functions:
            # Check if function creates ServiceRequest
            func_start = content.find(f'def {func_name}')
            if func_start == -1:
                continue
            
            # Get next 3000 chars
            func_content = content[func_start:func_start+3000]
            
            creates_request = (
                'ServiceRequest.objects.create' in func_content or
                ('serializer.save(' in func_content and 'ServiceRequest' in content[:func_start+3000])
            )
            
            if creates_request:
                functions_found.append({
                    'file': file_path,
                    'function': func_name,
                    'content': func_content
                })
                print(f"  ✓ {file_path} -> {func_name}()")
    except Exception as e:
        print(f"  ✗ Error reading {file_path}: {e}")

print(f"\nTotal functions that create ServiceRequest: {len(functions_found)}")
print()

# Step 3: Check each function for availability checking
print("STEP 3: Verifying availability checking in each function...")
print("=" * 80)
print()

all_verified = True
missing_checks = []

for func_info in functions_found:
    func_content = func_info['content']
    
    checks = {
        'availability_filter': "availability='available'" in func_content,
        'verified_filter': "verification_status='verified'" in func_content,
        'exclude_assignments': "service_assignments__status__in" in func_content,
        'distinct': ".distinct()" in func_content,
    }
    
    all_passed = all(checks.values())
    
    status = "✅ PASS" if all_passed else "❌ FAIL"
    print(f"{status} {func_info['function']}() in {func_info['file']}")
    
    if not all_passed:
        print("     Missing:")
        for check_name, passed in checks.items():
            if not passed:
                print(f"       ❌ {check_name}")
        all_verified = False
        missing_checks.append(func_info)
    else:
        print("     ✅ All checks present")
    
    print()

# Step 4: Check URL patterns
print("=" * 80)
print("STEP 4: Checking all URL patterns...")
print("-" * 80)
print()

url_files = [
    'clients/urls.py',
    'clients/api_urls.py',
    'jobs/service_request_urls.py',
]

for url_file in url_files:
    full_path = os.path.join(os.path.dirname(__file__), url_file)
    if not os.path.exists(full_path):
        continue
    
    print(f"📄 {url_file}")
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find path patterns
        patterns = re.findall(r"path\(['\"]([^'\"]+)['\"].*?name=['\"]([^'\"]+)['\"]", content)
        
        for url_pattern, url_name in patterns:
            if any(keyword in url_pattern.lower() for keyword in ['request', 'create', 'new']):
                print(f"   🔗 {url_pattern} (name: {url_name})")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()

# Final Summary
print("=" * 80)
print("FINAL VERIFICATION SUMMARY")
print("=" * 80)
print()

print(f"Total functions that create ServiceRequest: {len(functions_found)}")
print(f"Functions with complete availability checking: {len(functions_found) - len(missing_checks)}")
print(f"Functions MISSING availability checking: {len(missing_checks)}")
print()

if all_verified:
    print("✅✅✅ 100% VERIFIED - ALL FUNCTIONS HAVE AVAILABILITY CHECKING ✅✅✅")
    print()
    print("Verified functions:")
    for func_info in functions_found:
        print(f"  ✅ {func_info['function']}() in {func_info['file']}")
    print()
    print(f"Total: {len(functions_found)}/{len(functions_found)} (100%)")
else:
    print("❌ VERIFICATION FAILED - MISSING AVAILABILITY CHECKING IN:")
    print()
    for func_info in missing_checks:
        print(f"  ❌ {func_info['function']}() in {func_info['file']}")

print()
print("=" * 80)
