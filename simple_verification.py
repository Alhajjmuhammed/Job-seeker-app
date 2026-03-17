#!/usr/bin/env python
"""
Simple verification of availability checking in all ServiceRequest creation endpoints
"""

import os
import re

print("=" * 80)
print("FINAL VERIFICATION - ALL SERVICE REQUEST ENTRY POINTS")
print("=" * 80)
print()

# Files that create ServiceRequest
files_to_check = [
    'clients/service_request_web_views.py',
    'clients/views.py', 
    'clients/api_views.py',
    'clients/service_request_client_views.py',
]

all_functions = []

for file_path in files_to_check:
    if not os.path.exists(file_path):
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all function definitions
    func_pattern = r'def\s+(\w+)\s*\([^)]*\):'
    functions = re.findall(func_pattern, content)
    
    for func_name in functions:
        # Find function content
        func_start = content.find(f'def {func_name}')
        if func_start == -1:
            continue
        
        # Get function content (approximate - up to 3000 chars)
        func_content = content[func_start:func_start+3000]
        
        # Check if it creates ServiceRequest
        creates_request = (
            'ServiceRequest.objects.create' in func_content or
            ('serializer.save(' in func_content and 'ServiceRequestSerializer' in content)
        )
        
        if creates_request:
            all_functions.append({
                'file': file_path,
                'function': func_name,
                'content': func_content
            })

print(f"Found {len(all_functions)} functions that create ServiceRequest:\n")

# Check availability checking in each
all_verified = True
for func_info in all_functions:
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
    
    if all_passed:
        print("     ✅ availability='available'")
        print("     ✅ verification_status='verified'")
        print("     ✅ exclude service_assignments__status__in")
        print("     ✅ .distinct()")
    else:
        print("     Missing checks:")
        for check_name, passed in checks.items():
            if not passed:
                print(f"       ❌ {check_name}")
        all_verified = False
    
    print()

# Final summary
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)
print()

if all_verified:
    print(f"✅✅✅ 100% VERIFIED ✅✅✅")
    print()
    print(f"ALL {len(all_functions)} FUNCTIONS HAVE COMPLETE AVAILABILITY CHECKING:")
    print()
    for func_info in all_functions:
        print(f"  ✅ {func_info['function']}() in {func_info['file']}")
    print()
    print(f"Coverage: {len(all_functions)}/{len(all_functions)} (100%)")
else:
    print(f"❌ VERIFICATION FAILED")
    print(f"Some functions are missing availability checking")

print()
print("=" * 80)
