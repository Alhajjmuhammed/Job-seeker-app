#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM TEST - Find ALL issues and gaps
Tests every aspect of the platform systematically
"""
import requests
import json
import time
import random
import string
import os

BASE_URL = "http://127.0.0.1:8000"

class ComprehensiveSystemTest:
    def __init__(self):
        self.issues = []
        self.auth_token = None
        self.test_user_email = None
        
    def log_issue(self, severity, category, issue, details=""):
        """Log an issue found during testing"""
        self.issues.append({
            'severity': severity,
            'category': category, 
            'issue': issue,
            'details': details
        })
        print(f"   🚨 {severity} ISSUE: {issue}")
        if details:
            print(f"      Details: {details}")
    
    def test_server_connectivity(self):
        """Test basic server connectivity and response"""
        print("🌐 TESTING SERVER CONNECTIVITY")
        print("-" * 60)
        
        try:
            response = requests.get(f"{BASE_URL}/api/config/terms/", timeout=5)
            if response.status_code == 200:
                print("   ✅ Server is responsive")
                return True
            else:
                self.log_issue("CRITICAL", "Infrastructure", "Server not responding properly", 
                             f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_issue("CRITICAL", "Infrastructure", "Cannot connect to server", str(e))
            return False
    
    def test_all_api_endpoints(self):
        """Test every single API endpoint we can find"""
        print("\n🔗 TESTING ALL API ENDPOINTS")
        print("-" * 60)
        
        # Comprehensive list of endpoints to test
        endpoints = {
            # Authentication endpoints
            "Authentication": [
                ("/api/accounts/auth/login/", "POST", {"email": "test@test.com", "password": "test"}),
                ("/api/accounts/auth/register/", "POST", {"email": "test@test.com", "password": "test123", "password2": "test123", "firstName": "Test", "lastName": "User", "userType": "worker"}),
                ("/api/accounts/auth/logout/", "POST", {}),
                ("/api/accounts/auth/user/", "GET", None),
                ("/api/accounts/auth/csrf/", "GET", None),
            ],
            
            # Worker endpoints
            "Worker Management": [
                ("/api/workers/profile/", "GET", None),
                ("/api/workers/profile/", "POST", {"bio": "test bio"}),
                ("/api/workers/categories/", "GET", None),
                ("/api/workers/documents/upload/", "POST", {}),
            ],
            
            # Client endpoints  
            "Client Management": [
                ("/api/clients/profile/", "GET", None),
                ("/api/clients/profile/", "POST", {"company_name": "Test Company"}),
                ("/api/clients/jobs/", "GET", None),
                ("/api/clients/jobs/", "POST", {"title": "Test Job"}),
            ],
            
            # Job system
            "Job System": [
                ("/api/jobs/jobs/browse/", "GET", None),
                ("/api/jobs/worker/jobs/", "GET", None),
                ("/api/jobs/client/jobs/", "GET", None),
                ("/api/jobs/search/", "GET", None),
            ],
            
            # Core features
            "Core Features": [
                ("/api/config/terms/", "GET", None),
                ("/api/support/faq/", "GET", None),
                ("/api/notifications/", "GET", None),
            ],
            
            # Search system
            "Search System": [
                ("/api/search/", "GET", None),
                ("/api/jobs/search/", "GET", None),
            ]
        }
        
        total_endpoints = 0
        working_endpoints = 0
        
        for category, endpoint_list in endpoints.items():
            print(f"\n  {category}:")
            
            for endpoint_data in endpoint_list:
                endpoint = endpoint_data[0]
                method = endpoint_data[1]  
                data = endpoint_data[2]
                total_endpoints += 1
                
                try:
                    headers = {}
                    if self.auth_token:
                        headers['Authorization'] = f'Token {self.auth_token}'
                    
                    if method == "GET":
                        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
                    elif method == "POST":
                        response = requests.post(f"{BASE_URL}{endpoint}", json=data, headers=headers, timeout=10)
                    
                    status = response.status_code
                    
                    # Determine if response is acceptable
                    acceptable_codes = [200, 201, 400, 401, 403, 405, 429]  # 429 = rate limited (security working)
                    
                    if status in acceptable_codes:
                        print(f"    ✅ {method} {endpoint} → {status}")
                        working_endpoints += 1
                    elif status == 404:
                        self.log_issue("HIGH", "API", f"Endpoint not found: {method} {endpoint}")
                        print(f"    ❌ {method} {endpoint} → {status} (NOT FOUND)")
                    elif status == 500:
                        self.log_issue("CRITICAL", "API", f"Server error: {method} {endpoint}")
                        print(f"    ❌ {method} {endpoint} → {status} (SERVER ERROR)")
                    else:
                        self.log_issue("MEDIUM", "API", f"Unexpected response: {method} {endpoint}", f"Status: {status}")
                        print(f"    ⚠️ {method} {endpoint} → {status}")
                        
                except Exception as e:
                    self.log_issue("HIGH", "API", f"Connection error: {method} {endpoint}", str(e))
                    print(f"    💥 {method} {endpoint} → ERROR")
        
        endpoint_coverage = (working_endpoints / total_endpoints) * 100 if total_endpoints > 0 else 0
        print(f"\n  📊 Endpoint Coverage: {working_endpoints}/{total_endpoints} ({endpoint_coverage:.1f}%)")
        
        return endpoint_coverage
    
    def test_authentication_flow(self):
        """Test complete authentication flow"""
        print("\n🔐 TESTING COMPLETE AUTHENTICATION FLOW")
        print("-" * 60)
        
        # Generate unique test user
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.test_user_email = f"test_{suffix}@example.com"
        password = "SecureTestPass123!"
        
        # Test 1: Registration
        print("  1️⃣ Testing Registration...")
        register_data = {
            'email': self.test_user_email,
            'password': password,
            'password2': password,
            'firstName': 'Test',
            'lastName': 'User',
            'userType': 'worker',
            'phone': '+1234567890'
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/accounts/auth/register/", json=register_data, timeout=10)
            if response.status_code == 201:
                print("    ✅ Registration successful")
            elif response.status_code == 400:
                error_data = response.json()
                self.log_issue("HIGH", "Authentication", "Registration validation failed", str(error_data))
            elif response.status_code == 429:
                print("    ✅ Registration rate limited (security working)")
            else:
                self.log_issue("HIGH", "Authentication", "Registration failed", f"Status: {response.status_code}")
        except Exception as e:
            self.log_issue("HIGH", "Authentication", "Registration error", str(e))
        
        # Test 2: Login
        print("  2️⃣ Testing Login...")
        login_data = {
            'email': self.test_user_email,
            'password': password
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/accounts/auth/login/", json=login_data, timeout=10)
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data.get('token')
                print("    ✅ Login successful")
                if not self.auth_token:
                    self.log_issue("HIGH", "Authentication", "No token returned from login")
            elif response.status_code == 429:
                print("    ✅ Login rate limited (security working)")
            else:
                self.log_issue("HIGH", "Authentication", "Login failed", f"Status: {response.status_code}")
        except Exception as e:
            self.log_issue("HIGH", "Authentication", "Login error", str(e))
        
        # Test 3: Authenticated requests
        if self.auth_token:
            print("  3️⃣ Testing Authenticated Requests...")
            auth_endpoints = [
                "/api/accounts/auth/user/",
                "/api/notifications/",
            ]
            
            for endpoint in auth_endpoints:
                try:
                    headers = {'Authorization': f'Token {self.auth_token}'}
                    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
                    if response.status_code == 200:
                        print(f"    ✅ {endpoint} working with auth")
                    else:
                        self.log_issue("MEDIUM", "Authentication", f"Auth endpoint failed: {endpoint}", f"Status: {response.status_code}")
                except Exception as e:
                    self.log_issue("HIGH", "Authentication", f"Auth endpoint error: {endpoint}", str(e))
    
    def test_database_integrity(self):
        """Test database and data consistency"""
        print("\n💾 TESTING DATABASE INTEGRITY")
        print("-" * 60)
        
        # Check if migrations are applied
        try:
            import subprocess
            result = subprocess.run(['python', 'manage.py', 'showmigrations'], 
                                  capture_output=True, text=True, cwd='.')
            if result.returncode == 0:
                applied = result.stdout.count('[X]')
                unapplied = result.stdout.count('[ ]')
                print(f"  📊 Migrations: {applied} applied, {unapplied} pending")
                
                if unapplied > 0:
                    self.log_issue("HIGH", "Database", f"{unapplied} unapplied migrations")
            else:
                self.log_issue("MEDIUM", "Database", "Cannot check migrations")
        except Exception as e:
            self.log_issue("MEDIUM", "Database", "Migration check failed", str(e))
    
    def test_file_handling(self):
        """Test file upload and handling"""
        print("\n📁 TESTING FILE HANDLING")
        print("-" * 60)
        
        # Test file upload endpoints
        file_endpoints = [
            "/api/workers/documents/upload/",
        ]
        
        for endpoint in file_endpoints:
            try:
                headers = {}
                if self.auth_token:
                    headers['Authorization'] = f'Token {self.auth_token}'
                
                # Test with empty file data
                response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
                
                if response.status_code in [400, 401]:  # Expected for missing file
                    print(f"  ✅ {endpoint} handles missing file correctly")
                elif response.status_code == 404:
                    self.log_issue("HIGH", "File Handling", f"File upload endpoint not found: {endpoint}")
                else:
                    print(f"  ⚠️ {endpoint} returned {response.status_code}")
                    
            except Exception as e:
                self.log_issue("MEDIUM", "File Handling", f"File endpoint error: {endpoint}", str(e))
    
    def test_error_handling(self):
        """Test error handling and edge cases"""
        print("\n⚠️ TESTING ERROR HANDLING")
        print("-" * 60)
        
        error_tests = [
            # Malformed requests
            ("/api/accounts/auth/login/", "POST", {"invalid": "data"}),
            ("/api/workers/profile/", "POST", {"invalid": "x" * 10000}),  # Large data
            # Non-existent resources
            ("/api/workers/profile/999999/", "GET", None),
            ("/api/jobs/jobs/999999/", "GET", None),
        ]
        
        for endpoint, method, data in error_tests:
            try:
                headers = {}
                if self.auth_token:
                    headers['Authorization'] = f'Token {self.auth_token}'
                
                if method == "GET":
                    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=5)
                elif method == "POST":
                    response = requests.post(f"{BASE_URL}{endpoint}", json=data, headers=headers, timeout=5)
                
                # Check if error is handled gracefully (no 500 errors)
                if response.status_code < 500:
                    print(f"  ✅ {endpoint} handles errors gracefully ({response.status_code})")
                else:
                    self.log_issue("HIGH", "Error Handling", f"Server error on: {endpoint}", f"Status: {response.status_code}")
                    
            except Exception as e:
                print(f"  ⚠️ {endpoint} connection error (expected for some tests)")
    
    def run_comprehensive_test(self):
        """Run all tests and generate comprehensive report"""
        print("🧪 COMPREHENSIVE SYSTEM TEST - FINDING ALL ISSUES")
        print("=" * 80)
        
        # Test 1: Basic connectivity
        if not self.test_server_connectivity():
            print("❌ Cannot proceed - server connectivity failed")
            return
        
        # Test 2: Database integrity
        self.test_database_integrity()
        
        # Test 3: Complete authentication flow
        self.test_authentication_flow()
        
        # Test 4: All API endpoints
        endpoint_coverage = self.test_all_api_endpoints()
        
        # Test 5: File handling
        self.test_file_handling()
        
        # Test 6: Error handling
        self.test_error_handling()
        
        # Generate final report
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE TEST RESULTS")
        print("=" * 80)
        
        if not self.issues:
            print("🎉 NO ISSUES FOUND! System appears to be working perfectly!")
            print(f"📊 Endpoint Coverage: {endpoint_coverage:.1f}%")
        else:
            print(f"🚨 FOUND {len(self.issues)} ISSUES THAT NEED FIXING:")
            print()
            
            # Group issues by severity
            critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
            high_issues = [i for i in self.issues if i['severity'] == 'HIGH']
            medium_issues = [i for i in self.issues if i['severity'] == 'MEDIUM']
            
            if critical_issues:
                print("🔥 CRITICAL ISSUES (Must fix immediately):")
                for issue in critical_issues:
                    print(f"  • {issue['category']}: {issue['issue']}")
                    if issue['details']:
                        print(f"    → {issue['details']}")
                print()
            
            if high_issues:
                print("🚨 HIGH PRIORITY ISSUES:")
                for issue in high_issues:
                    print(f"  • {issue['category']}: {issue['issue']}")
                    if issue['details']:
                        print(f"    → {issue['details']}")
                print()
            
            if medium_issues:
                print("⚠️ MEDIUM PRIORITY ISSUES:")
                for issue in medium_issues:
                    print(f"  • {issue['category']}: {issue['issue']}")
                    if issue['details']:
                        print(f"    → {issue['details']}")
                print()
        
        return self.issues

if __name__ == "__main__":
    tester = ComprehensiveSystemTest()
    issues = tester.run_comprehensive_test()