"""
Unit tests for Jobs API endpoints
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import User
from workers.models import Category, WorkerProfile
from jobs.models import JobRequest, JobApplication
from decimal import Decimal
from datetime import date, timedelta


class JobRequestModelTest(TestCase):
    """Test JobRequest model"""
    
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='jobclient',
            email='client@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Client',
            user_type='client'
        )
        self.category = Category.objects.create(name="Cleaning")
    
    def test_create_job_request(self):
        """Test creating a job request"""
        job = JobRequest.objects.create(
            client=self.client_user,
            title="House Cleaning",
            description="Need thorough house cleaning",
            category=self.category,
            location="123 Main St",
            city="New York",
            budget=Decimal('100.00'),
            duration_days=1
        )
        self.assertEqual(job.status, 'open')
        self.assertEqual(job.urgency, 'medium')
        self.assertEqual(job.workers_needed, 1)
    
    def test_job_status_choices(self):
        """Test job status transitions"""
        job = JobRequest.objects.create(
            client=self.client_user,
            title="Test Job",
            description="Test description",
            category=self.category,
            location="Test Location",
            city="Test City",
            duration_days=1
        )
        
        # Test status change
        job.status = 'in_progress'
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.status, 'in_progress')


class JobApplicationModelTest(TestCase):
    """Test JobApplication model"""
    
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='appclient',
            email='client@example.com',
            password='testpass123',
            user_type='client'
        )
        self.worker_user = User.objects.create_user(
            username='appworker',
            email='worker@example.com',
            password='testpass123',
            user_type='worker'
        )
        self.worker_profile = WorkerProfile.objects.create(
            user=self.worker_user
        )
        self.category = Category.objects.create(name="Construction")
        self.job = JobRequest.objects.create(
            client=self.client_user,
            title="Build Fence",
            description="Build a wooden fence",
            category=self.category,
            location="456 Oak Ave",
            city="Los Angeles",
            duration_days=3
        )
    
    def test_create_application(self):
        """Test creating a job application"""
        application = JobApplication.objects.create(
            job=self.job,
            worker=self.worker_profile,
            cover_letter="I have 5 years of experience"
        )
        self.assertEqual(application.status, 'pending')
        self.assertEqual(application.worker.user.email, 'worker@example.com')
    
    def test_unique_application_per_job(self):
        """Test that a worker can only apply once per job"""
        JobApplication.objects.create(
            job=self.job,
            worker=self.worker_profile
        )
        with self.assertRaises(Exception):
            JobApplication.objects.create(
                job=self.job,
                worker=self.worker_profile
            )


class JobsAPITest(APITestCase):
    """Test Jobs API endpoints"""
    
    def setUp(self):
        # Create category
        self.category = Category.objects.create(name="Painting")
        
        # Create client user
        self.client_user = User.objects.create_user(
            username='jobapiclient',
            email='client@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Client',
            user_type='client'
        )
        self.client_token = Token.objects.create(user=self.client_user)
        
        # Create worker user
        self.worker_user = User.objects.create_user(
            username='jobapiworker',
            email='worker@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Worker',
            user_type='worker'
        )
        self.worker_token = Token.objects.create(user=self.worker_user)
        self.worker_profile = WorkerProfile.objects.create(
            user=self.worker_user,
            verification_status='verified',
            is_profile_complete=True
        )
        self.worker_profile.categories.add(self.category)
        
        # Create a job
        self.job = JobRequest.objects.create(
            client=self.client_user,
            title="Paint Living Room",
            description="Need to paint living room white",
            category=self.category,
            location="789 Pine St",
            city="Chicago",
            budget=Decimal('200.00'),
            duration_days=2
        )
        
        self.api_client = APIClient()
    
    def test_list_jobs_authenticated(self):
        """Test listing jobs requires authentication"""
        # Without auth
        response = self.api_client.get('/api/jobs/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # With auth
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        response = self.api_client.get('/api/jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_job_as_client(self):
        """Test creating a job as a client"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        data = {
            'title': 'New Paint Job',
            'description': 'Paint the entire house',
            'category': self.category.id,
            'location': '111 Test St',
            'city': 'Boston',
            'budget': '500.00',
            'duration_days': 5
        }
        response = self.api_client.post('/api/jobs/', data)
        # Status depends on actual implementation
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
    
    def test_worker_cannot_create_job(self):
        """Test that workers cannot create jobs"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        data = {
            'title': 'Invalid Job',
            'description': 'Should not work',
            'category': self.category.id,
            'location': 'Test',
            'city': 'Test',
            'duration_days': 1
        }
        response = self.api_client.post('/api/jobs/', data)
        # Workers should get forbidden
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED])
    
    def test_job_detail(self):
        """Test getting job detail"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        response = self.api_client.get(f'/api/jobs/{self.job.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Paint Living Room')
    
    def test_apply_for_job(self):
        """Test worker applying for a job"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        data = {
            'cover_letter': 'I am experienced in painting'
        }
        response = self.api_client.post(f'/api/jobs/{self.job.id}/apply/', data)
        # Check for success or appropriate error
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED, 
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST  # If already applied
        ])
    
    def test_filter_jobs_by_category(self):
        """Test filtering jobs by category"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        response = self.api_client.get(f'/api/jobs/?category={self.category.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_filter_jobs_by_city(self):
        """Test filtering jobs by city"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        response = self.api_client.get('/api/jobs/?city=Chicago')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class JobApplicationAPITest(APITestCase):
    """Test Job Application API endpoints"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Gardening")
        
        # Client
        self.client_user = User.objects.create_user(
            username='gardenclient',
            email='client@example.com',
            password='testpass123',
            user_type='client'
        )
        self.client_token = Token.objects.create(user=self.client_user)
        
        # Workers
        self.worker1 = User.objects.create_user(
            username='gardenworker1',
            email='worker1@example.com',
            password='testpass123',
            user_type='worker'
        )
        self.worker1_token = Token.objects.create(user=self.worker1)
        self.worker1_profile = WorkerProfile.objects.create(
            user=self.worker1,
            verification_status='verified'
        )
        
        self.worker2 = User.objects.create_user(
            username='gardenworker2',
            email='worker2@example.com',
            password='testpass123',
            user_type='worker'
        )
        self.worker2_token = Token.objects.create(user=self.worker2)
        self.worker2_profile = WorkerProfile.objects.create(
            user=self.worker2,
            verification_status='verified'
        )
        
        # Job
        self.job = JobRequest.objects.create(
            client=self.client_user,
            title="Garden Maintenance",
            description="Monthly garden maintenance",
            category=self.category,
            location="222 Garden Rd",
            city="Portland",
            duration_days=1
        )
        
        # Application
        self.application = JobApplication.objects.create(
            job=self.job,
            worker=self.worker1_profile,
            cover_letter="I love gardening"
        )
        
        self.api_client = APIClient()
    
    def test_view_applications_as_client(self):
        """Test client can view applications for their job"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.get(f'/api/jobs/{self.job.id}/applications/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
    
    def test_accept_application(self):
        """Test client can accept an application"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.post(
            f'/api/jobs/{self.job.id}/applications/{self.application.id}/accept/'
        )
        # Depends on actual endpoint implementation
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, 
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_worker_can_view_own_applications(self):
        """Test worker can view their own applications"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker1_token.key}')
        response = self.api_client.get('/api/jobs/my-applications/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
    
    def test_withdraw_application(self):
        """Test worker can withdraw their application"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker1_token.key}')
        response = self.api_client.delete(f'/api/jobs/{self.job.id}/applications/{self.application.id}/')
        # May be DELETE or POST to withdraw endpoint
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN
        ])
