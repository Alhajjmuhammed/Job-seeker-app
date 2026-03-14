"""
Comprehensive tests for Late Screenshot Upload (Web) feature
"""

import os
import tempfile
from io import BytesIO
from PIL import Image
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from jobs.service_request_models import ServiceRequest
from workers.models import Category
from worker_connect.notification_models import Notification

User = get_user_model()


class LateScreenshotUploadTestCase(TestCase):
    """Test late screenshot upload functionality for service requests"""
    
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
        
        self.admin_user = User.objects.create_user(
            username='testadmin',
            email='testadmin@example.com',
            password='adminpass123',
            user_type='client',
            is_staff=True,
            is_active=True,
            first_name='Test',
            last_name='Admin'
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
        
        # Create test service request
        self.service_request = ServiceRequest.objects.create(
            client=self.client_user,
            category=self.category,
            title='Test Service Request',
            description='Test Description',
            location='Test Location',
            city='Test City',
            urgency='normal',
            status='pending'
        )
        
        # Create Django test client
        self.test_client = Client()
    
    def create_test_image(self, name='test.jpg', format='JPEG', size=(100, 100)):
        """Helper method to create a test image"""
        file = BytesIO()
        image = Image.new('RGB', size, color='red')
        image.save(file, format)
        file.seek(0)
        return SimpleUploadedFile(
            name,
            file.read(),
            content_type=f'image/{format.lower()}'
        )
    
    def create_large_image(self, size_mb=6):
        """Helper method to create a large test image"""
        # Create image larger than 5MB
        file = BytesIO()
        # Approximate size calculation
        pixels = int((size_mb * 1024 * 1024) / 3)  # RGB = 3 bytes per pixel
        dimension = int(pixels ** 0.5)
        image = Image.new('RGB', (dimension, dimension), color='blue')
        image.save(file, 'JPEG')
        file.seek(0)
        return SimpleUploadedFile(
            'large_test.jpg',
            file.read(),
            content_type='image/jpeg'
        )
    
    def test_upload_screenshot_page_loads(self):
        """Test that upload screenshot page loads correctly"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service_requests/client/upload_screenshot.html')
        self.assertContains(response, 'Upload Payment Screenshot')
        self.assertContains(response, 'Request Info')
    
    def test_upload_valid_jpeg_screenshot(self):
        """Test uploading a valid JPEG screenshot"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        
        image = self.create_test_image('screenshot.jpg', 'JPEG')
        response = self.test_client.post(url, {'payment_screenshot': image})
        
        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)
        
        # Refresh service request from database
        self.service_request.refresh_from_db()
        
        # Check that screenshot was saved
        self.assertIsNotNone(self.service_request.payment_screenshot)
        self.assertFalse(self.service_request.payment_verified)
        self.assertIsNone(self.service_request.payment_verified_by)
        self.assertIsNone(self.service_request.payment_verified_at)
    
    def test_upload_valid_png_screenshot(self):
        """Test uploading a valid PNG screenshot"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        
        image = self.create_test_image('screenshot.png', 'PNG')
        response = self.test_client.post(url, {'payment_screenshot': image})
        
        self.assertEqual(response.status_code, 302)
        
        self.service_request.refresh_from_db()
        self.assertIsNotNone(self.service_request.payment_screenshot)
    
    def test_upload_invalid_file_type(self):
        """Test uploading an invalid file type"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        
        # Create a text file
        text_file = SimpleUploadedFile(
            'test.txt',
            b'This is not an image',
            content_type='text/plain'
        )
        
        response = self.test_client.post(url, {'payment_screenshot': text_file})
        
        # Should redirect back with error
        self.assertEqual(response.status_code, 302)
        
        # Service request should not have screenshot
        self.service_request.refresh_from_db()
        self.assertFalse(self.service_request.payment_screenshot)
    
    def test_upload_file_too_large(self):
        """Test uploading a file larger than 5MB"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        
        large_image = self.create_large_image(size_mb=6)
        response = self.test_client.post(url, {'payment_screenshot': large_image})
        
        # Should redirect back with error
        self.assertEqual(response.status_code, 302)
        
        # Service request should not have screenshot
        self.service_request.refresh_from_db()
        self.assertFalse(self.service_request.payment_screenshot)
    
    def test_upload_no_file_provided(self):
        """Test submitting form without selecting a file"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        
        response = self.test_client.post(url, {})
        
        # Should redirect back with error
        self.assertEqual(response.status_code, 302)
        
        # Service request should not have screenshot
        self.service_request.refresh_from_db()
        self.assertFalse(self.service_request.payment_screenshot)
    
    def test_upload_resets_verification_status(self):
        """Test that uploading new screenshot resets verification status"""
        # Mark as verified first
        self.service_request.payment_verified = True
        self.service_request.payment_verified_by = self.admin_user
        from django.utils import timezone
        self.service_request.payment_verified_at = timezone.now()
        self.service_request.save()
        
        # Upload new screenshot
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        
        image = self.create_test_image('new_screenshot.jpg', 'JPEG')
        response = self.test_client.post(url, {'payment_screenshot': image})
        
        # Verification status should be reset
        self.service_request.refresh_from_db()
        self.assertFalse(self.service_request.payment_verified)
        self.assertIsNone(self.service_request.payment_verified_by)
        self.assertIsNone(self.service_request.payment_verified_at)
    
    def test_admin_notification_on_upload(self):
        """Test that admin receives notification on screenshot upload"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        
        # Count existing notifications for admin
        initial_count = Notification.objects.filter(
            recipient=self.admin_user
        ).count()
        
        image = self.create_test_image('screenshot.jpg', 'JPEG')
        response = self.test_client.post(url, {'payment_screenshot': image})
        
        # Check that admin notification was created
        final_count = Notification.objects.filter(
            recipient=self.admin_user
        ).count()
        
        # Should have at least one more notification
        self.assertGreater(final_count, initial_count, "Admin should receive notification for screenshot upload")
    
    def test_unauthorized_user_cannot_access(self):
        """Test that other users cannot access upload page"""
        self.test_client.force_login(self.other_client)
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        
        response = self.test_client.get(url)
        
        # Should return 404 (get_object_or_404 with client filter)
        self.assertEqual(response.status_code, 404)
    
    def test_unauthenticated_user_redirected(self):
        """Test that unauthenticated user is redirected to login"""
        url = reverse('service_requests_web:client_upload_screenshot', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_detail_page_shows_upload_button(self):
        """Test that detail page shows upload button"""
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_detail', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload Payment Screenshot')
        self.assertContains(response, 'client_upload_screenshot')
    
    def test_detail_page_shows_screenshot_if_uploaded(self):
        """Test that detail page shows screenshot info if uploaded"""
        # Upload screenshot
        self.service_request.payment_screenshot = self.create_test_image()
        self.service_request.save()
        
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_detail', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Screenshot')
        self.assertContains(response, 'Update Screenshot')
        self.assertContains(response, 'View Screenshot')
    
    def test_detail_page_shows_verification_status(self):
        """Test that detail page shows verification status"""
        # Upload and verify screenshot
        self.service_request.payment_screenshot = self.create_test_image()
        self.service_request.payment_verified = True
        self.service_request.payment_verified_by = self.admin_user
        from django.utils import timezone
        self.service_request.payment_verified_at = timezone.now()
        self.service_request.save()
        
        self.test_client.force_login(self.client_user)
        url = reverse('service_requests_web:client_request_detail', args=[self.service_request.id])
        response = self.test_client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verified')
        self.assertContains(response, 'Test Admin')  # Verifier name
    
    def test_url_pattern_exists(self):
        """Test that URL pattern is properly configured"""
        url = reverse('service_requests_web:client_upload_screenshot', args=[1])
        self.assertEqual(url, '/services/client/request/1/upload-screenshot/')
    
    def tearDown(self):
        """Clean up uploaded files"""
        # Remove uploaded test files
        if self.service_request.payment_screenshot:
            if os.path.exists(self.service_request.payment_screenshot.path):
                os.remove(self.service_request.payment_screenshot.path)
