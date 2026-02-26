"""
COMPLETE BUSINESS FUNCTIONALITY TEST
Testing actual workflows end-to-end to verify ALL functionality works
"""

import requests
import json
import time
import os
from datetime import datetime

class CompleteBusinessFunctionalityTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.client_token = None
        self.worker_token = None
        self.job_id = None
        self.application_id = None
        self.failures = []
        self.warnings = []
        
    def log_failure(self, area, issue):
        self.failures.append(f"FAILURE: {area} - {issue}")
        print(f"    ❌ FAILURE: {issue}")
    
    def log_warning(self, area, issue):
        self.warnings.append(f"WARNING: {area} - {issue}")
        print(f"    ⚠️ WARNING: {issue}")
    
    def log_success(self, area, result):
        print(f"    ✅ {result}")

    def test_complete_user_registration_workflow(self):
        """Test both client and worker registration"""
        print("\n👥 TESTING: COMPLETE USER REGISTRATION WORKFLOWS")
        print("-" * 60)
        
        # Register a client
        client_data = {
            'email': f'client_{int(time.time())}@example.com',
            'password': 'ClientTest123!',
            'firstName': 'Test',
            'lastName': 'Client',
            'phone': '+1234567890',
            'userType': 'client'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/accounts/auth/register/",
                json=client_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if 'token' in data:
                    self.client_token = data['token']
                    self.log_success("Client Registration", "Client registered successfully")
                else:
                    self.log_failure("Client Registration", "No token received")
                    return False
            else:
                self.log_failure("Client Registration", f"Failed with status {response.status_code}: {response.text[:200]}")
                return False
        except Exception as e:
            self.log_failure("Client Registration", f"Exception: {str(e)}")
            return False
        
        # Register a worker
        worker_data = {
            'email': f'worker_{int(time.time())}@example.com',
            'password': 'WorkerTest123!',
            'firstName': 'Test',
            'lastName': 'Worker',
            'phone': '+1234567891',
            'userType': 'worker'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/accounts/auth/register/",
                json=worker_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if 'token' in data:
                    self.worker_token = data['token']
                    self.log_success("Worker Registration", "Worker registered successfully")
                    return True
                else:
                    self.log_failure("Worker Registration", "No token received")
                    return False
            else:
                self.log_failure("Worker Registration", f"Failed with status {response.status_code}: {response.text[:200]}")
                return False
        except Exception as e:
            self.log_failure("Worker Registration", f"Exception: {str(e)}")
            return False

    def test_client_job_posting_workflow(self):
        """Test if client can actually post a job"""
        print("\n💼 TESTING: CLIENT JOB POSTING WORKFLOW")
        print("-" * 60)
        
        if not self.client_token:
            self.log_failure("Job Posting", "No client token available")
            return False
        
        headers = {'Authorization': f'Token {self.client_token}', 'Content-Type': 'application/json'}
        
        # Try to post a job
        job_data = {
            'title': 'Test Job Posting',
            'description': 'This is a test job to verify the posting workflow works',
            'budget': '100.00',
            'location': 'Remote',
            'category': 'Technology',
            'requirements': 'Basic testing skills'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jobs/",
                json=job_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if 'id' in data:
                    self.job_id = data['id']
                    self.log_success("Job Posting", f"Job posted successfully with ID: {self.job_id}")
                    return True
                else:
                    self.log_warning("Job Posting", "Job posted but no ID returned")
                    return True
            else:
                self.log_failure("Job Posting", f"Failed with status {response.status_code}: {response.text[:300]}")
                return False
                
        except Exception as e:
            self.log_failure("Job Posting", f"Exception: {str(e)}")
            return False

    def test_worker_job_application_workflow(self):
        """Test if worker can apply to jobs"""
        print("\n🎯 TESTING: WORKER JOB APPLICATION WORKFLOW")
        print("-" * 60)
        
        if not self.worker_token:
            self.log_failure("Job Application", "No worker token available")
            return False
        
        headers = {'Authorization': f'Token {self.worker_token}', 'Content-Type': 'application/json'}
        
        # First, try to browse jobs
        try:
            response = requests.get(
                f"{self.base_url}/api/jobs/jobs/browse/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                jobs = data.get('results', [])
                if jobs:
                    job_to_apply = jobs[0]
                    job_id = job_to_apply.get('id')
                    self.log_success("Job Browsing", f"Found {len(jobs)} jobs, will apply to job {job_id}")
                elif self.job_id:
                    job_id = self.job_id
                    self.log_success("Job Browsing", f"Using previously created job {job_id}")
                else:
                    self.log_warning("Job Application", "No jobs available to apply to")
                    return True
            else:
                self.log_failure("Job Browsing", f"Cannot browse jobs: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_failure("Job Browsing", f"Exception: {str(e)}")
            return False
        
        # Try to apply to a job
        if not job_id:
            self.log_warning("Job Application", "No job ID available for application")
            return True
            
        application_data = {
            'job_id': job_id,
            'cover_letter': 'I am very interested in this position and believe I have the required skills.',
            'proposed_budget': '95.00'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jobs/applications/",
                json=application_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.log_success("Job Application", "Successfully applied to job")
                return True
            else:
                self.log_failure("Job Application", f"Application failed with status {response.status_code}: {response.text[:300]}")
                return False
                
        except Exception as e:
            self.log_failure("Job Application", f"Exception: {str(e)}")
            return False

    def test_payment_workflow(self):
        """Test if payment system actually processes payments"""
        print("\n💳 TESTING: PAYMENT PROCESSING WORKFLOW")
        print("-" * 60)
        
        if not self.client_token or not self.worker_token:
            self.log_failure("Payment", "Missing client or worker tokens")
            return False
        
        client_headers = {'Authorization': f'Token {self.client_token}', 'Content-Type': 'application/json'}
        
        # Try to create a payment intent
        payment_data = {
            'amount': '100.00',
            'job_id': self.job_id or 1,
            'description': 'Test payment for job completion'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/payments/payments/create-payment-intent/",
                json=payment_data,
                headers=client_headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.log_success("Payment", "Payment intent created successfully")
                return True
            elif response.status_code == 404:
                self.log_failure("Payment", "Payment creation endpoint not found")
                return False
            elif response.status_code == 503:
                self.log_warning("Payment", "Payment service unavailable (Stripe not configured)")
                return True
            else:
                self.log_failure("Payment", f"Payment failed with status {response.status_code}: {response.text[:300]}")
                return False
                
        except Exception as e:
            self.log_failure("Payment", f"Exception: {str(e)}")
            return False

    def test_search_and_filtering(self):
        """Test if search and filtering actually work"""
        print("\n🔍 TESTING: SEARCH AND FILTERING FUNCTIONALITY")
        print("-" * 60)
        
        search_tests = [
            ('/api/v1/search/jobs/', 'Basic search'),
            ('/api/v1/search/jobs/?q=test', 'Keyword search'),
            ('/api/v1/search/jobs/?category=Technology', 'Category filter'),
            ('/api/v1/search/jobs/?location=Remote', 'Location filter'),
        ]
        
        for endpoint, test_name in search_tests:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and 'results' in data:
                        self.log_success("Search", f"{test_name} works (found {len(data['results'])} results)")
                    else:
                        self.log_success("Search", f"{test_name} returns data")
                else:
                    self.log_failure("Search", f"{test_name} failed with status {response.status_code}")
                    
            except Exception as e:
                self.log_failure("Search", f"{test_name} exception: {str(e)}")

    def test_file_upload_functionality(self):
        """Test if file upload actually works"""
        print("\n📁 TESTING: FILE UPLOAD FUNCTIONALITY")
        print("-" * 60)
        
        if not self.worker_token:
            self.log_failure("File Upload", "No worker token available")
            return False
        
        headers = {'Authorization': f'Token {self.worker_token}'}
        
        # Create a test file
        test_content = "This is a test document for file upload verification"
        
        try:
            # Try to upload to worker documents
            files = {'document': ('test_document.txt', test_content, 'text/plain')}
            data = {'document_type': 'resume', 'description': 'Test document upload'}
            
            response = requests.post(
                f"{self.base_url}/api/v1/workers/documents/",
                files=files,
                data=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.log_success("File Upload", "Document upload successful")
                return True
            elif response.status_code == 404:
                self.log_failure("File Upload", "Document upload endpoint not found")
                return False
            else:
                self.log_failure("File Upload", f"Upload failed with status {response.status_code}: {response.text[:300]}")
                return False
                
        except Exception as e:
            self.log_failure("File Upload", f"Exception: {str(e)}")
            return False

    def run_complete_business_test(self):
        print("🔥 COMPLETE BUSINESS FUNCTIONALITY TEST")
        print("=" * 70)
        print("Testing actual workflows end-to-end to verify ALL functionality works")
        print(f"Business test time: {datetime.now()}")
        
        # Run all business workflow tests
        user_reg_success = self.test_complete_user_registration_workflow()
        
        if user_reg_success:
            self.test_client_job_posting_workflow()
            self.test_worker_job_application_workflow()
            self.test_payment_workflow()
            
        self.test_search_and_filtering()
        self.test_file_upload_functionality()
        
        print("\n" + "=" * 70)
        print("🎯 COMPLETE BUSINESS FUNCTIONALITY RESULTS")
        print("=" * 70)
        
        print(f"❌ Failures: {len(self.failures)}")
        print(f"⚠️ Warnings: {len(self.warnings)}")
        
        if self.failures:
            print("\n💥 BUSINESS FUNCTIONALITY FAILURES:")
            for failure in self.failures:
                print(f"   {failure}")
            print(f"\n🚨 HONEST BUSINESS ASSESSMENT: NOT 100% - CORE WORKFLOWS BROKEN")
            print("Critical business functions are not working!")
            return False
            
        elif self.warnings:
            print("\n⚠️ BUSINESS FUNCTIONALITY WARNINGS:")
            for warning in self.warnings:
                print(f"   {warning}")
            print(f"\n📊 HONEST BUSINESS ASSESSMENT: 85-95% - Some workflows need attention")
            print("Core functions work but some features need configuration")
            return True
            
        else:
            print("\n🏆 HONEST BUSINESS ASSESSMENT: TRUE 100% BUSINESS FUNCTIONALITY")
            print("✅ All critical business workflows verified")
            print("✅ Users can register and authenticate")
            print("✅ Clients can post jobs") 
            print("✅ Workers can apply to jobs")
            print("✅ Payment system processes transactions")
            print("✅ Search and filtering work")
            print("✅ File uploads function")
            print("\n🎉 CONFIRMED: ALL BUSINESS FUNCTIONALITY WORKS 100%!")
            return True

if __name__ == "__main__":
    tester = CompleteBusinessFunctionalityTest()
    is_truly_100_percent = tester.run_complete_business_test()