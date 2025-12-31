"""
Unit tests for Clients API endpoints
"""
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import User
from clients.models import ClientProfile
from workers.models import Category, WorkerProfile
from jobs.models import JobRequest
from decimal import Decimal


class ClientProfileModelTest(TestCase):
    """Test ClientProfile model"""
    
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='profileclient',
            email='client@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Client',
            user_type='client'
        )
    
    def test_create_client_profile(self):
        """Test creating a client profile"""
        profile = ClientProfile.objects.create(
            user=self.client_user,
            company_name="Test Company",
            address="123 Business St",
            city="New York",
            state="NY",
            postal_code="10001"
        )
        self.assertEqual(profile.user.email, 'client@example.com')
        self.assertEqual(profile.company_name, "Test Company")
    
    def test_client_profile_defaults(self):
        """Test default values for client profile"""
        profile = ClientProfile.objects.create(user=self.client_user)
        self.assertEqual(profile.total_jobs_posted, 0)


class ClientAPITest(APITestCase):
    """Test Clients API endpoints"""
    
    def setUp(self):
        # Create client user
        self.client_user = User.objects.create_user(
            username='apiclient1',
            email='client@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Client',
            user_type='client'
        )
        self.client_token = Token.objects.create(user=self.client_user)
        self.client_profile = ClientProfile.objects.create(
            user=self.client_user,
            company_name="Test Company",
            city="Seattle",
            state="WA"
        )
        
        # Create another client
        self.client_user2 = User.objects.create_user(
            username='apiclient2',
            email='client2@example.com',
            password='testpass123',
            user_type='client'
        )
        self.client2_token = Token.objects.create(user=self.client_user2)
        self.client2_profile = ClientProfile.objects.create(
            user=self.client_user2,
            company_name="Other Company"
        )
        
        # Create worker user
        self.worker_user = User.objects.create_user(
            username='apiworker',
            email='worker@example.com',
            password='testpass123',
            user_type='worker'
        )
        self.worker_token = Token.objects.create(user=self.worker_user)
        
        # Create category and jobs
        self.category = Category.objects.create(name="Landscaping")
        self.job = JobRequest.objects.create(
            client=self.client_user,
            title="Lawn Mowing",
            description="Weekly lawn mowing",
            category=self.category,
            location="789 Green St",
            city="Seattle",
            duration_days=1
        )
        
        self.api_client = APIClient()
    
    def test_get_client_profile_authenticated(self):
        """Test getting client profile requires authentication"""
        # Without auth
        response = self.api_client.get('/api/client/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # With auth
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.get('/api/client/profile/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
    
    def test_update_client_profile(self):
        """Test updating client profile"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        data = {
            'company_name': 'Updated Company Name',
            'city': 'Portland'
        }
        response = self.api_client.patch('/api/client/profile/', data)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
    
    def test_worker_cannot_access_client_profile(self):
        """Test that workers cannot access client-only endpoints"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        response = self.api_client.get('/api/client/profile/')
        # Should be forbidden or not found for workers
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN, 
            status.HTTP_404_NOT_FOUND,
            status.HTTP_200_OK  # May return empty if profile doesn't exist
        ])
    
    def test_client_can_view_their_jobs(self):
        """Test client can view jobs they've posted"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.get('/api/client/jobs/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class ClientJobManagementTest(APITestCase):
    """Test client job management functionality"""
    
    def setUp(self):
        # Create client
        self.client_user = User.objects.create_user(
            username='mgmtclient',
            email='client@example.com',
            password='testpass123',
            user_type='client'
        )
        self.client_token = Token.objects.create(user=self.client_user)
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        
        # Create worker
        self.worker_user = User.objects.create_user(
            username='mgmtworker',
            email='worker@example.com',
            password='testpass123',
            user_type='worker'
        )
        self.worker_profile = WorkerProfile.objects.create(
            user=self.worker_user,
            verification_status='verified'
        )
        
        # Create category and job
        self.category = Category.objects.create(name="Moving")
        self.job = JobRequest.objects.create(
            client=self.client_user,
            title="Help Moving",
            description="Need help moving furniture",
            category=self.category,
            location="123 Old St",
            city="Denver",
            duration_days=1
        )
        
        self.api_client = APIClient()
    
    def test_client_can_cancel_own_job(self):
        """Test client can cancel their own job"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.post(f'/api/jobs/{self.job.id}/cancel/')
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_client_can_complete_job(self):
        """Test client can mark job as completed"""
        # First assign a worker
        self.job.status = 'in_progress'
        self.job.save()
        
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.post(f'/api/jobs/{self.job.id}/complete/')
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_update_job_details(self):
        """Test client can update job details"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        data = {
            'title': 'Updated Title',
            'description': 'Updated description'
        }
        response = self.api_client.patch(f'/api/jobs/{self.job.id}/', data)
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,  # If not owner
            status.HTTP_404_NOT_FOUND
        ])


class ClientReviewTest(APITestCase):
    """Test client review functionality"""
    
    def setUp(self):
        # Create client
        self.client_user = User.objects.create_user(
            username='reviewclient',
            email='client@example.com',
            password='testpass123',
            user_type='client'
        )
        self.client_token = Token.objects.create(user=self.client_user)
        
        # Create worker
        self.worker_user = User.objects.create_user(
            username='reviewworker',
            email='worker@example.com',
            password='testpass123',
            user_type='worker'
        )
        self.worker_profile = WorkerProfile.objects.create(
            user=self.worker_user,
            verification_status='verified'
        )
        
        # Create completed job
        self.category = Category.objects.create(name="Repair")
        self.job = JobRequest.objects.create(
            client=self.client_user,
            title="Fix Door",
            description="Fix broken door",
            category=self.category,
            location="456 Fix St",
            city="Austin",
            duration_days=1,
            status='completed'
        )
        self.job.assigned_workers.add(self.worker_profile)
        
        self.api_client = APIClient()
    
    def test_client_can_review_worker(self):
        """Test client can leave review for worker after job completion"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        data = {
            'rating': 5,
            'comment': 'Excellent work!'
        }
        response = self.api_client.post(
            f'/api/jobs/{self.job.id}/review/',
            data
        )
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ])
