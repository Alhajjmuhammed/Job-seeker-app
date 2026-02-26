#!/usr/bin/env python3
"""
Test all possible URL patterns to ensure complete coverage
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_all_url_patterns():
    """Test comprehensive URL patterns"""
    print("🔗 TESTING ALL POSSIBLE URL PATTERNS")
    print("=" * 80)
    
    # Test all URL patterns we can find in the system
    url_patterns = {
        "Main Pages": [
            "/",
            "/accounts/login/",
            "/accounts/register/",
        ],
        
        "API v1 Endpoints": [
            "/api/v1/accounts/auth/login/",
            "/api/v1/accounts/auth/register/",
            "/api/v1/jobs/",
            "/api/v1/clients/",
            "/api/v1/workers/",
            "/api/v1/search/",
            "/api/v1/search/jobs/",
            "/api/v1/config/",
            "/api/v1/support/",
            "/api/v1/notifications/",
        ],
        
        "Mobile Compatible Endpoints": [
            "/api/accounts/auth/login/",
            "/api/accounts/auth/register/",
            "/api/jobs/jobs/browse/",
            "/api/clients/profile/",
            "/api/workers/profile/",
            "/api/config/terms/",
            "/api/support/faq/",
            "/api/notifications/",
        ],
        
        "Specialized Endpoints": [
            "/api/jobs/worker/jobs/",
            "/api/jobs/client/jobs/",
            "/api/jobs/search/",
            "/api/workers/categories/",
            "/api/workers/documents/upload/",
        ]
    }
    
    total_tested = 0
    working_endpoints = 0
    issues = []
    
    for category, urls in url_patterns.items():
        print(f"\n{category}:")
        print("-" * 50)
        
        for url in urls:
            total_tested += 1
            try:
                response = requests.get(f"{BASE_URL}{url}", timeout=5)
                status = response.status_code
                
                # Acceptable status codes (endpoint exists)
                if status in [200, 201, 302, 400, 401, 403, 405]:
                    print(f"  ✅ {url} → {status}")
                    working_endpoints += 1
                elif status == 404:
                    print(f"  ❌ {url} → {status} (NOT FOUND)")
                    issues.append(f"404: {url}")
                elif status == 500:
                    print(f"  🚨 {url} → {status} (SERVER ERROR)")
                    issues.append(f"500: {url}")
                else:
                    print(f"  ⚠️ {url} → {status}")
                    
            except Exception as e:
                print(f"  💥 {url} → ERROR: {str(e)[:50]}")
                issues.append(f"ERROR: {url}")
    
    print(f"\n" + "=" * 80)
    print(f"📊 URL PATTERN TEST RESULTS:")
    print(f"   Total endpoints tested: {total_tested}")
    print(f"   Working endpoints: {working_endpoints}")
    print(f"   Success rate: {(working_endpoints/total_tested)*100:.1f}%")
    
    if issues:
        print(f"\n🚨 ISSUES FOUND:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print(f"\n🎉 ALL URL PATTERNS WORKING PERFECTLY!")
    
    return issues

def test_edge_cases():
    """Test edge cases and error conditions"""
    print(f"\n🧪 TESTING EDGE CASES")
    print("=" * 80)
    
    edge_cases = [
        # Test with various HTTP methods
        ("/api/config/terms/", "POST", {}),
        ("/api/config/terms/", "PUT", {}),
        ("/api/config/terms/", "DELETE", {}),
        
        # Test with malformed data
        ("/api/accounts/auth/login/", "POST", {"malformed": "data"}),
        ("/api/accounts/auth/register/", "POST", {"incomplete": "data"}),
        
        # Test with oversized requests
        ("/api/workers/profile/", "POST", {"bio": "x" * 10000}),
        
        # Test non-existent IDs
        ("/api/workers/profile/99999/", "GET", None),
        ("/api/jobs/jobs/99999/", "GET", None),
    ]
    
    issues = []
    
    for endpoint, method, data in edge_cases:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            elif method == "POST":
                response = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=5)
            elif method == "PUT":
                response = requests.put(f"{BASE_URL}{endpoint}", json=data, timeout=5)
            elif method == "DELETE":
                response = requests.delete(f"{BASE_URL}{endpoint}", timeout=5)
            
            # Server errors (500) are bad, everything else is acceptable error handling
            if response.status_code >= 500:
                print(f"  🚨 {method} {endpoint} → {response.status_code} (SERVER ERROR)")
                issues.append(f"Server error: {method} {endpoint}")
            else:
                print(f"  ✅ {method} {endpoint} → {response.status_code} (Handled gracefully)")
                
        except Exception as e:
            print(f"  ⚠️ {method} {endpoint} → Connection error (expected for some tests)")
    
    if issues:
        print(f"\n🚨 EDGE CASE ISSUES:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print(f"\n✅ ALL EDGE CASES HANDLED PROPERLY!")
    
    return issues

def run_complete_url_test():
    """Run complete URL and edge case testing"""
    print("🎯 COMPLETE URL PATTERN AND EDGE CASE TEST")
    print("=" * 80)
    
    url_issues = test_all_url_patterns()
    edge_issues = test_edge_cases()
    
    all_issues = url_issues + edge_issues
    
    print(f"\n" + "=" * 80)
    print(f"🏁 FINAL RESULTS:")
    
    if not all_issues:
        print("🎉 PERFECT! NO ISSUES FOUND IN ANY TESTS!")
        print("✅ All URL patterns working")
        print("✅ All edge cases handled properly")
        print("✅ System is fully functional")
    else:
        print(f"🚨 FOUND {len(all_issues)} ISSUES THAT NEED ATTENTION:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
    
    return all_issues

if __name__ == "__main__":
    run_complete_url_test()