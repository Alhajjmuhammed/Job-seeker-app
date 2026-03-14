"""
Comprehensive tests for Activity Tracking (Web) feature
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from jobs.service_request_models import ServiceRequest, WorkerActivity
from workers.models import Category, WorkerProfile

User = get_user_model()


class ActivityTrackingWebTestCase(TestCase):
    """Test activity tracking web interface for clients"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.client_user = User.objects.create_user(
            username='testclient',
            email='testclient@example.com',
            password='testpass123',
            user_type='client',
            first_name='Test',
            last_name='Client'
        )
        
        self.worker_user = User.objects.create_user(
            username='testworker',
            email='testworker@example.com',
            password='testpass123',
            user_type='worker',
            first_name='Test',
            last_name='Worker'
        )
        
        self.other_client = User.objects.create_user(
            username='otherclient',
            email='otherclient@example.com',
            password='testpass123',
            user_type='client',
            first_name='Other',
            last_name='Client'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Description',
            is_active=True
        )
        
        # Create worker profile
        self.worker_profile = WorkerProfile.objects.create(
            user=self.worker_user,
            bio='Test worker bio',
            availability='available'
        )
        self.worker_profile.categories.add(self.category)
        
        # Create test service request
        self.service_request = ServiceRequest.objects.create(
            client=self.client_user,
            category=self.category,
            title='Test Service Request',
            description='Test Description',
            location='Test Location',
            city='Test City',
            urgency='normal',
            status='in_progress',
            assigned_worker=self.worker_profile
        )
        
        # Create test activities
        WorkerActivity.objects.create(
            worker=self.worker_profile,
            service_request=self.service_request,
            activity_type='assigned',
            description='Worker was assigned to this service'
        )
        
        WorkerActivity.objects.create(
            worker=self.worker_profile,
            service_request=self.service_request,
            activity_type='accepted',
            description='Worker accepted the assignment'
        )
        
        WorkerActivity.objects.create(
            worker=self.worker_profile,
            service_request=self.service_request,
            activity_type='started',
            description='Worker started working on the service'
        )
        
        # Create Django test client
        self.test_client = Client()
    
    def test_activity_page_loads(self):
        """Test that activity page loads correctly"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_activity', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service_requests/client/activity.html')
        self.assertContains(response, 'Activity Log')
        self.assertContains(response, 'Test Service Request')
    
    def test_activity_page_shows_activities(self):
        """Test that activity page displays activities"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_activity', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'assigned')
        self.assertContains(response, 'accepted')
        self.assertContains(response, 'started')
        self.assertContains(response, 'Worker was assigned')
    
    def test_activity_filter_by_type(self):
        """Test filtering activities by type"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_activity', args=[self.service_request.id])
        
        # Filter by accepted
        response = self.test_client.get(url, {'type': 'accepted'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'accepted')
        
        # Filter by started
        response = self.test_client.get(url, {'type': 'started'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'started')
    
    def test_unauthorized_user_cannot_access(self):
        """Test that other users cannot view activity"""
        self.test_client.force_login(self.other_client)
        url = reverse('service_requests_web:client_request_activity', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        # Should return 404 since get_object_or_404 filters by client
        self.assertEqual(response.status_code, 404)
    
    def test_unauthenticated_user_redirected(self):
        """Test that unauthenticated user is redirected to login"""
        url = reverse('service_requests_web:client_request_activity', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_detail_page_has_activity_button(self):
        """Test that detail page has 'View Activity Log' button"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_detail', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Activity Log')
        self.assertContains(response, 'client_request_activity')
    
    def test_activity_pagination(self):
        """Test that pagination works for many activities"""
        # Create 25 activities
        for i in range(25):
            WorkerActivity.objects.create(
                worker=self.worker_profile,
                service_request=self.service_request,
                activity_type='paused',
                description=f'Activity #{i}'
            )
        
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_activity', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should show pagination (20 per page)
        self.assertContains(response, 'Page')
    
    def test_no_activities_message(self):
        """Test message when no activities exist"""
        # Create a new request with no activities
        new_request = ServiceRequest.objects.create(
            client=self.client_user,
            category=self.category,
            title='New Request',
            description='New Description',
            location='New Location',
            city='New City',
            urgency='normal',
            status='pending'
        )
        
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_activity', args=[new_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Activities Yet')
    
    def test_url_pattern_exists(self):
        """Test that URL pattern is properly configured"""
        url = reverse('service_requests_web:client_request_activity', args=[1])
        self.assertEqual(url, '/services/client/request/1/activity/')
    
    def test_activity_displays_metadata(self):
        """Test that activity metadata (location, duration) displays"""
        from datetime import timedelta
        
        # Create activity with metadata
        WorkerActivity.objects.create(
            worker=self.worker_profile,
            service_request=self.service_request,
            activity_type='completed',
            description='Work completed',
            location='123 Main St',
            duration=timedelta(hours=2, minutes=30)
        )
        
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_activity', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '123 Main St')
