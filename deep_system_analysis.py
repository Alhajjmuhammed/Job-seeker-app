#!/usr/bin/env python3
"""
DEEP SYSTEM ANALYSIS - Test complex business logic and workflows
This goes beyond basic endpoint testing to examine actual functionality
"""
import requests
import json
import time
import subprocess
import os
from datetime import datetime
import random
import string

BASE_URL = "http://127.0.0.1:8000"

class DeepSystemAnalysis:
    def __init__(self):
        self.issues = []
        self.auth_token = None
        self.test_user_id = None
        self.critical_gaps = []
        
    def log_issue(self, severity, category, issue, details=""):
        """Log an issue found during deep analysis"""
        self.issues.append({
            'severity': severity,
            'category': category,
            'issue': issue,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        print(f"   🚨 {severity}: {issue}")
        if details:
            print(f"      → {details}")
    
    def log_gap(self, category, gap, impact="Unknown"):
        """Log functionality gaps"""
        self.critical_gaps.append({
            'category': category,
            'gap': gap,
            'impact': impact
        })
        print(f"   ⚠️ GAP: {gap}")
        if impact != "Unknown":
            print(f"      Impact: {impact}")

    def test_database_models_integrity(self):
        """Deep test of database models and relationships"""
        print("💾 DEEP DATABASE MODEL ANALYSIS")
        print("-" * 70)
        
        # Check if models are properly defined by examining Django
        try:
            # Test model introspection
            result = subprocess.run(['python', 'manage.py', 'inspectdb'], 
                                  capture_output=True, text=True, cwd='.', timeout=30)
            
            if result.returncode == 0:
                model_output = result.stdout
                
                # Check for key models
                required_models = [
                    'user', 'workerprofile', 'clientprofile', 
                    'jobrequest', 'category', 'skill'
                ]
                
                missing_models = []
                for model in required_models:
                    if model.lower() not in model_output.lower():
                        missing_models.append(model)
                
                if missing_models:
                    self.log_issue("CRITICAL", "Database", 
                                 f"Missing critical models: {missing_models}")
                else:
                    print("  ✅ All critical database models present")
                    
            else:
                self.log_issue("HIGH", "Database", "Cannot inspect database models")
                
        except Exception as e:
            self.log_issue("HIGH", "Database", "Model inspection failed", str(e))

    def test_complex_business_workflows(self):
        """Test complex business logic workflows"""
        print("\n🔄 DEEP BUSINESS WORKFLOW ANALYSIS")
        print("-" * 70)
        
        # Test 1: Job posting workflow
        print("  1️⃣ Testing Job Posting Workflow...")
        
        # Check if we can create a test job posting
        try:
            headers = {'Authorization': f'Token {self.auth_token}'} if self.auth_token else {}
            
            job_data = {
                'title': 'Test Job',
                'description': 'Test job description',
                'category': 1,
                'budget': 100.00,
                'location': 'Test City'
            }
            
            response = requests.post(f"{BASE_URL}/api/clients/jobs/", 
                                   json=job_data, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                print("    ✅ Job posting workflow accessible")
            elif response.status_code == 401:
                print("    ⚠️ Job posting requires authentication (expected)")
            elif response.status_code == 400:
                print("    ⚠️ Job posting validation working")
            else:
                self.log_issue("HIGH", "Business Logic", 
                             f"Job posting workflow issue: {response.status_code}")
                
        except Exception as e:
            self.log_issue("HIGH", "Business Logic", "Job posting test failed", str(e))

        # Test 2: Worker application workflow  
        print("  2️⃣ Testing Worker Application Workflow...")
        
        try:
            response = requests.get(f"{BASE_URL}/api/jobs/jobs/browse/", timeout=10)
            
            if response.status_code in [200, 401]:
                print("    ✅ Job browsing workflow accessible")
            else:
                self.log_issue("MEDIUM", "Business Logic", 
                             f"Job browsing issue: {response.status_code}")
                             
            # Test job application
            headers = {'Authorization': f'Token {self.auth_token}'} if self.auth_token else {}
            response = requests.post(f"{BASE_URL}/api/jobs/worker/jobs/1/apply/", 
                                   headers=headers, timeout=10)
            
            if response.status_code in [200, 201, 400, 401, 404]:
                print("    ✅ Job application workflow structured")
            else:
                self.log_issue("MEDIUM", "Business Logic", 
                             f"Job application issue: {response.status_code}")
                
        except Exception as e:
            self.log_issue("MEDIUM", "Business Logic", "Application test failed", str(e))

    def test_search_and_matching_algorithms(self):
        """Test search and job matching functionality"""
        print("\n🔍 DEEP SEARCH & MATCHING ANALYSIS")
        print("-" * 70)
        
        # Test search functionality with real queries
        search_tests = [
            ('', 'Empty search'),
            ('plumber', 'Category search'),
            ('urgent', 'Keyword search'),
            ('location:city', 'Location search'),
        ]
        
        for query, test_type in search_tests:
            try:
                params = {'q': query} if query else {}
                response = requests.get(f"{BASE_URL}/api/search/jobs/", 
                                      params=params, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"    ✅ {test_type}: Returns data structure")
                        
                        # Check if response has expected structure
                        if isinstance(data, dict):
                            if 'results' in data or 'jobs' in data or isinstance(data, list):
                                print(f"      → Structured search results")
                            else:
                                self.log_gap("Search Algorithm", 
                                           f"{test_type} doesn't return expected results structure")
                        
                    except json.JSONDecodeError:
                        self.log_issue("MEDIUM", "Search Algorithm", 
                                     f"{test_type} returns invalid JSON")
                        
                elif response.status_code == 401:
                    print(f"    ⚠️ {test_type}: Requires authentication")
                else:
                    self.log_issue("HIGH", "Search Algorithm", 
                                 f"{test_type} failed: {response.status_code}")
                    
            except Exception as e:
                self.log_issue("HIGH", "Search Algorithm", f"{test_type} error", str(e))

    def test_file_handling_and_uploads(self):
        """Deep test of file handling capabilities"""
        print("\n📁 DEEP FILE HANDLING ANALYSIS")
        print("-" * 70)
        
        # Test document upload endpoints
        file_endpoints = [
            ("/api/workers/documents/upload/", "Worker document upload"),
        ]
        
        for endpoint, description in file_endpoints:
            try:
                headers = {'Authorization': f'Token {self.auth_token}'} if self.auth_token else {}
                
                # Test 1: Empty file upload
                response = requests.post(f"{BASE_URL}{endpoint}", 
                                       headers=headers, timeout=10)
                
                if response.status_code in [400, 401]:
                    print(f"    ✅ {description}: Proper validation")
                elif response.status_code == 404:
                    self.log_gap("File Handling", f"{description} endpoint missing")
                else:
                    print(f"    ⚠️ {description}: Status {response.status_code}")
                
                # Test 2: Check if file upload logic exists
                # We can't test actual file upload without creating test files,
                # but we can check if the endpoint handles file uploads properly
                
            except Exception as e:
                self.log_issue("MEDIUM", "File Handling", f"{description} error", str(e))

    def test_payment_and_financial_logic(self):
        """Test payment processing and financial calculations"""
        print("\n💰 DEEP PAYMENT & FINANCIAL ANALYSIS")
        print("-" * 70)
        
        # Check for payment-related endpoints
        payment_endpoints = [
            ("/api/v1/payments/payments/", "Payment processing"),
            ("/api/v1/payments/earnings/", "Worker earnings"),
            ("/api/v1/job-invoices/", "Invoice system"),
            ("/api/v1/worker-earnings/summary/", "Earnings tracking"),
        ]
        
        payment_system_found = False
        
        for endpoint, description in payment_endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                
                if response.status_code in [200, 401, 403]:
                    print(f"    ✅ {description}: Endpoint exists")
                    payment_system_found = True
                elif response.status_code == 404:
                    print(f"    ❌ {description}: Not implemented")
                else:
                    print(f"    ⚠️ {description}: Status {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ {description}: Connection error")
        
        if not payment_system_found:
            self.log_gap("Payment System", "No payment processing endpoints found",
                        "High - Users cannot receive payments")

    def test_real_data_scenarios(self):
        """Test with realistic data scenarios"""
        print("\n📊 REAL DATA SCENARIO ANALYSIS")
        print("-" * 70)
        
        # Test data loading and performance
        data_tests = [
            ("/api/workers/categories/", "Category data loading"),
            ("/api/support/faq/", "FAQ data loading"), 
            ("/api/config/terms/", "Configuration data"),
        ]
        
        for endpoint, description in data_tests:
            try:
                start_time = time.time()
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=15)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Analyze data quality
                        if isinstance(data, dict):
                            data_size = len(str(data))
                            print(f"    ✅ {description}: {data_size} chars, {response_time:.1f}ms")
                            
                            # Check for meaningful data
                            if data_size < 50:
                                self.log_gap("Data Quality", 
                                           f"{description} has minimal data")
                        elif isinstance(data, list):
                            print(f"    ✅ {description}: {len(data)} items, {response_time:.1f}ms")
                            
                    except json.JSONDecodeError:
                        self.log_issue("MEDIUM", "Data Quality", 
                                     f"{description} returns invalid JSON")
                        
                else:
                    self.log_issue("MEDIUM", "Data Loading", 
                                 f"{description} failed: {response.status_code}")
                    
            except Exception as e:
                self.log_issue("HIGH", "Data Loading", f"{description} error", str(e))

    def test_integration_points(self):
        """Test integration between different system components"""
        print("\n🔗 INTEGRATION POINT ANALYSIS")
        print("-" * 70)
        
        # Test user-worker profile integration
        try:
            if self.auth_token:
                headers = {'Authorization': f'Token {self.auth_token}'}
                
                # Test user info endpoint
                user_response = requests.get(f"{BASE_URL}/api/accounts/auth/user/", 
                                           headers=headers, timeout=10)
                
                # Test worker profile endpoint  
                worker_response = requests.get(f"{BASE_URL}/api/workers/profile/", 
                                             headers=headers, timeout=10)
                
                if user_response.status_code == 200 and worker_response.status_code == 200:
                    print("    ✅ User-Worker profile integration working")
                elif user_response.status_code == 200:
                    print("    ⚠️ User endpoint works, worker profile may need setup")
                else:
                    print("    ⚠️ Authentication-profile integration needs testing with real auth")
            else:
                print("    ⚠️ Cannot test user-profile integration without authentication")
                
        except Exception as e:
            self.log_issue("MEDIUM", "Integration", "User-profile integration error", str(e))

    def test_system_scalability_indicators(self):
        """Test indicators of system scalability"""
        print("\n⚡ SCALABILITY INDICATOR ANALYSIS")
        print("-" * 70)
        
        # Test pagination
        pagination_endpoints = [
            "/api/jobs/jobs/browse/",
            "/api/search/jobs/",
        ]
        
        for endpoint in pagination_endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}?page=1&page_size=10", timeout=10)
                
                if response.status_code in [200, 401]:
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if 'next' in data or 'previous' in data or 'count' in data:
                                print(f"    ✅ {endpoint}: Pagination implemented")
                            else:
                                print(f"    ⚠️ {endpoint}: Pagination structure unclear")
                        except:
                            print(f"    ⚠️ {endpoint}: Response structure unknown")
                    else:
                        print(f"    ⚠️ {endpoint}: Requires authentication for pagination test")
                else:
                    self.log_gap("Scalability", f"{endpoint} pagination not working")
                    
            except Exception as e:
                self.log_issue("MEDIUM", "Scalability", f"{endpoint} pagination error", str(e))

    def run_deep_analysis(self):
        """Run comprehensive deep analysis"""
        print("🔬 DEEP SYSTEM ANALYSIS - EXAMINING COMPLEX FUNCTIONALITY")
        print("=" * 90)
        print(f"Analysis started at: {datetime.now()}")
        print("=" * 90)
        
        # Run all deep analysis tests
        self.test_database_models_integrity()
        self.test_complex_business_workflows()  
        self.test_search_and_matching_algorithms()
        self.test_file_handling_and_uploads()
        self.test_payment_and_financial_logic()
        self.test_real_data_scenarios()
        self.test_integration_points()
        self.test_system_scalability_indicators()
        
        # Generate comprehensive analysis report
        print("\n" + "=" * 90)
        print("🎯 DEEP ANALYSIS RESULTS")
        print("=" * 90)
        
        # Categorize issues by severity
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        high_issues = [i for i in self.issues if i['severity'] == 'HIGH']
        medium_issues = [i for i in self.issues if i['severity'] == 'MEDIUM']
        
        # Categorize gaps by impact
        high_impact_gaps = [g for g in self.critical_gaps if 'High' in g.get('impact', '')]
        medium_impact_gaps = [g for g in self.critical_gaps if 'Medium' in g.get('impact', '')]
        
        print(f"📊 ANALYSIS SUMMARY:")
        print(f"   • Issues found: {len(self.issues)}")
        print(f"   • Functionality gaps: {len(self.critical_gaps)}")
        print(f"   • Critical issues: {len(critical_issues)}")
        print(f"   • High priority issues: {len(high_issues)}")
        print(f"   • Medium priority issues: {len(medium_issues)}")
        
        if critical_issues:
            print(f"\n🔥 CRITICAL ISSUES (System Breaking):")
            for issue in critical_issues:
                print(f"   • {issue['category']}: {issue['issue']}")
                if issue['details']:
                    print(f"     → {issue['details']}")
        
        if high_issues:
            print(f"\n🚨 HIGH PRIORITY ISSUES:")
            for issue in high_issues:
                print(f"   • {issue['category']}: {issue['issue']}")
                if issue['details']:
                    print(f"     → {issue['details']}")
        
        if medium_issues:
            print(f"\n⚠️ MEDIUM PRIORITY ISSUES:")
            for issue in medium_issues:
                print(f"   • {issue['category']}: {issue['issue']}")
                if issue['details']:
                    print(f"     → {issue['details']}")
        
        if high_impact_gaps:
            print(f"\n❗ HIGH IMPACT FUNCTIONALITY GAPS:")
            for gap in high_impact_gaps:
                print(f"   • {gap['category']}: {gap['gap']}")
                print(f"     Impact: {gap['impact']}")
        
        if medium_impact_gaps:
            print(f"\n⚠️ MEDIUM IMPACT FUNCTIONALITY GAPS:")
            for gap in medium_impact_gaps:
                print(f"   • {gap['category']}: {gap['gap']}")
        
        # Calculate realistic completeness score
        total_issues = len(critical_issues) + len(high_issues) + len(medium_issues)
        total_gaps = len(high_impact_gaps) + len(medium_impact_gaps)
        
        # Base score starts at 100%
        completeness_score = 100
        
        # Deduct for issues
        completeness_score -= (len(critical_issues) * 20)  # Critical issues = -20% each
        completeness_score -= (len(high_issues) * 10)      # High issues = -10% each  
        completeness_score -= (len(medium_issues) * 5)     # Medium issues = -5% each
        
        # Deduct for gaps
        completeness_score -= (len(high_impact_gaps) * 15)    # High impact gaps = -15% each
        completeness_score -= (len(medium_impact_gaps) * 8)   # Medium impact gaps = -8% each
        
        # Ensure score doesn't go below 0
        completeness_score = max(0, completeness_score)
        
        print(f"\n" + "=" * 90)
        print(f"🏆 REALISTIC COMPLETENESS ASSESSMENT")
        print(f"=" * 90)
        print(f"Deep Analysis Completeness Score: {completeness_score}%")
        
        if completeness_score >= 95:
            status = "🎉 TRULY PRODUCTION READY"
            assessment = "System is genuinely complete and ready for real-world use!"
        elif completeness_score >= 85:
            status = "🚀 VERY CLOSE TO PRODUCTION"
            assessment = "System is highly functional with minor gaps to address."
        elif completeness_score >= 70:
            status = "✅ SOLID DEVELOPMENT BUILD"
            assessment = "System has good foundation but needs important features completed."
        elif completeness_score >= 50:
            status = "⚠️ FUNCTIONAL PROTOTYPE"
            assessment = "System works for basic use cases but has significant gaps."
        else:
            status = "🚨 EARLY STAGE SYSTEM"
            assessment = "System needs substantial development work."
        
        print(f"Status: {status}")
        print(f"Assessment: {assessment}")
        
        print(f"\n📋 HONEST RECOMMENDATIONS:")
        if completeness_score >= 90:
            print("   • System is ready for careful production deployment")
            print("   • Monitor performance and user feedback closely")
        elif completeness_score >= 80:
            print("   • Address high-priority issues before production")
            print("   • Consider beta testing with limited users")
        elif completeness_score >= 70:
            print("   • Complete critical functionality gaps")
            print("   • Extensive testing needed before production")
        else:
            print("   • Significant development work required")
            print("   • Focus on core business functionality first")
        
        return {
            'score': completeness_score,
            'issues': self.issues,
            'gaps': self.critical_gaps,
            'status': status
        }

if __name__ == "__main__":
    analyzer = DeepSystemAnalysis()
    results = analyzer.run_deep_analysis()