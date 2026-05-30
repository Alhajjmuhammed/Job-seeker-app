"""
Tests for the accounts app - Authentication API
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTest(TestCase):
    """Tests for the custom User model"""
    
    def test_create_user_with_email(self):
        """Test creating a user with email is successful"""
        email = 'test@example.com'
        password = 'TestPass123!'
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name='Test',
            last_name='User',
            user_type='worker'
        )
        
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertEqual(user.user_type, 'worker')
    
    def test_email_is_unique(self):
        """Test that email uniqueness is enforced"""
        email = 'unique@example.com'
        User.objects.create_user(
            username=email,
            email=email,
            password='TestPass123!',
            user_type='worker'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='another@example.com',
                email=email,  # Same email
                password='TestPass123!',
                user_type='client'
            )
    
    def test_user_type_properties(self):
        """Test is_worker and is_client properties"""
        worker = User.objects.create_user(
            username='worker@test.com',
            email='worker@test.com',
            password='TestPass123!',
            user_type='worker'
        )
        client = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='TestPass123!',
            user_type='client'
        )
        
        self.assertTrue(worker.is_worker)
        self.assertFalse(worker.is_client)
        self.assertTrue(client.is_client)
        self.assertFalse(client.is_worker)


class RegistrationAPITest(APITestCase):
    """Tests for the registration API"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
    
    def test_register_worker_success(self):
        """Test successful worker registration"""
        data = {
            'firstName': 'John',
            'lastName': 'Doe',
            'email': 'john@example.com',
            'phone': '+1234567890',
            'password': 'SecurePass123!',
            'userType': 'worker',
            'workerType': 'professional'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'john@example.com')
        self.assertEqual(response.data['user']['userType'], 'worker')
    
    def test_register_client_success(self):
        """Test successful client registration"""
        data = {
            'firstName': 'Jane',
            'lastName': 'Doe',
            'email': 'jane@example.com',
            'phone': '+1234567890',
            'password': 'SecurePass123!',
            'userType': 'client'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['userType'], 'client')
    
    def test_register_duplicate_email(self):
        """Test registration with existing email fails"""
        # Create first user
        User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='TestPass123!',
            user_type='worker'
        )
        
        # Try to register with same email
        data = {
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'existing@example.com',
            'phone': '+1234567890',
            'password': 'SecurePass123!',
            'userType': 'worker'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_weak_password(self):
        """Test registration with weak password fails"""
        data = {
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'weak@example.com',
            'phone': '+1234567890',
            'password': '123',  # Too weak
            'userType': 'worker'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_invalid_email(self):
        """Test registration with invalid email fails"""
        data = {
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'not-an-email',
            'phone': '+1234567890',
            'password': 'SecurePass123!',
            'userType': 'worker'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAPITest(APITestCase):
    """Tests for the login API"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/auth/login/'
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            user_type='worker'
        )
    
    def test_login_success(self):
        """Test successful login"""
        data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
    
    def test_login_wrong_password(self):
        """Test login with wrong password fails"""
        data = {
            'email': 'testuser@example.com',
            'password': 'WrongPassword123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent email fails"""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_missing_fields(self):
        """Test login with missing fields fails"""
        response = self.client.post(self.login_url, {'email': 'test@example.com'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutAPITest(APITestCase):
    """Tests for the logout API"""
    
    def setUp(self):
        self.client = APIClient()
        self.logout_url = '/api/auth/logout/'
        
        # Create and authenticate a test user
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='TestPass123!',
            user_type='worker'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
    
    def test_logout_success(self):
        """Test successful logout"""
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify token is deleted
        self.assertFalse(Token.objects.filter(user=self.user).exists())
    
    def test_logout_unauthenticated(self):
        """Test logout without authentication fails"""
        self.client.credentials()  # Remove credentials
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CurrentUserAPITest(APITestCase):
    """Tests for the current user API"""
    
    def setUp(self):
        self.client = APIClient()
        self.me_url = '/api/auth/me/'
        
        # Create and authenticate a test user
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            user_type='worker',
            phone_number='+1234567890'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
    
    def test_get_current_user(self):
        """Test getting current user info"""
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'testuser@example.com')
        self.assertEqual(response.data['firstName'], 'Test')
        self.assertEqual(response.data['lastName'], 'User')
        self.assertEqual(response.data['userType'], 'worker')
    
    def test_get_current_user_unauthenticated(self):
        """Test getting current user without auth fails"""
        self.client.credentials()  # Remove credentials
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RateLimitingTest(APITestCase):
    """Tests for API rate limiting"""
    
    def test_login_rate_limit(self):
        """Test that login endpoint has rate limiting"""
        login_url = '/api/auth/login/'
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        # Make multiple requests to trigger rate limit
        # The limit is 5/minute, so 6 requests should trigger it
        responses = []
        for _ in range(7):
            response = self.client.post(login_url, data, format='json')
            responses.append(response.status_code)
        
        # At least one should be rate limited (429)
        self.assertIn(429, responses)
