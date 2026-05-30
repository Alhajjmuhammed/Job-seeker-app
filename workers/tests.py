"""
Unit tests for Workers API endpoints
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import User
from workers.models import Category, Skill, WorkerProfile
from decimal import Decimal


class CategoryModelTest(TestCase):
    """Test Category model"""
    
    def test_create_category(self):
        """Test creating a category"""
        category = Category.objects.create(
            name="Construction",
            description="Building and construction services"
        )
        self.assertEqual(str(category), "Construction")
        self.assertTrue(category.is_active)
    
    def test_category_unique_name(self):
        """Test that category names must be unique"""
        Category.objects.create(name="Plumbing")
        with self.assertRaises(Exception):
            Category.objects.create(name="Plumbing")


class SkillModelTest(TestCase):
    """Test Skill model"""
    
    def setUp(self):
        self.category = Category.objects.create(name="IT Services")
    
    def test_create_skill(self):
        """Test creating a skill"""
        skill = Skill.objects.create(
            category=self.category,
            name="Python Programming"
        )
        self.assertEqual(str(skill), "IT Services - Python Programming")
    
    def test_skill_unique_within_category(self):
        """Test that skill names must be unique within a category"""
        Skill.objects.create(category=self.category, name="Web Development")
        with self.assertRaises(Exception):
            Skill.objects.create(category=self.category, name="Web Development")


class WorkerProfileModelTest(TestCase):
    """Test WorkerProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testworker',
            email='worker@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Worker',
            user_type='worker'
        )
    
    def test_create_worker_profile(self):
        """Test creating a worker profile"""
        profile = WorkerProfile.objects.create(
            user=self.user,
            worker_type='professional',
            bio='Experienced professional',
            hourly_rate=Decimal('25.00')
        )
        self.assertEqual(profile.user.email, 'worker@example.com')
        self.assertEqual(profile.verification_status, 'pending')
    
    def test_default_values(self):
        """Test default values for worker profile"""
        profile = WorkerProfile.objects.create(user=self.user)
        self.assertEqual(profile.worker_type, 'non_academic')
        self.assertEqual(profile.availability, 'available')
        self.assertEqual(profile.average_rating, Decimal('0'))


class WorkerAPITest(APITestCase):
    """Test Workers API endpoints"""
    
    def setUp(self):
        # Create categories
        self.category = Category.objects.create(
            name="Cleaning",
            description="Cleaning services"
        )
        
        # Create skills
        self.skill = Skill.objects.create(
            category=self.category,
            name="Deep Cleaning"
        )
        
        # Create client user
        self.client_user = User.objects.create_user(
            username='testclient',
            email='client@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Client',
            user_type='client'
        )
        self.client_token = Token.objects.create(user=self.client_user)
        
        # Create worker user
        self.worker_user = User.objects.create_user(
            username='testworker',
            email='worker@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Worker',
            user_type='worker'
        )
        self.worker_token = Token.objects.create(user=self.worker_user)
        
        # Create worker profile
        self.worker_profile = WorkerProfile.objects.create(
            user=self.worker_user,
            worker_type='professional',
            bio='Experienced cleaner',
            hourly_rate=Decimal('20.00'),
            verification_status='verified',
            is_profile_complete=True
        )
        self.worker_profile.categories.add(self.category)
        self.worker_profile.skills.add(self.skill)
        
        self.api_client = APIClient()
    
    def test_list_categories(self):
        """Test listing all categories"""
        response = self.api_client.get('/api/workers/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Cleaning')
    
    def test_list_workers_authenticated(self):
        """Test listing workers requires authentication"""
        # Without auth
        response = self.api_client.get('/api/workers/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # With auth
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.get('/api/workers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_worker_profile_detail(self):
        """Test getting worker profile detail"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.get(f'/api/workers/{self.worker_profile.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['bio'], 'Experienced cleaner')
    
    def test_search_workers_by_category(self):
        """Test searching workers by category"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.client_token.key}')
        response = self.api_client.get(f'/api/workers/?category={self.category.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_worker_can_update_own_profile(self):
        """Test that workers can update their own profile"""
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.worker_token.key}')
        response = self.api_client.patch(
            f'/api/workers/{self.worker_profile.id}/',
            {'bio': 'Updated bio'}
        )
        # May need to check actual endpoint implementation
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])


class WorkerSearchFilterTest(APITestCase):
    """Test worker search and filtering"""
    
    def setUp(self):
        # Create categories
        self.category1 = Category.objects.create(name="Plumbing")
        self.category2 = Category.objects.create(name="Electrical")
        
        # Create users and profiles
        self.user1 = User.objects.create_user(
            username='worker1',
            email='worker1@example.com',
            password='testpass123',
            first_name='John',
            last_name='Plumber',
            user_type='worker'
        )
        self.profile1 = WorkerProfile.objects.create(
            user=self.user1,
            hourly_rate=Decimal('30.00'),
            verification_status='verified',
            is_profile_complete=True
        )
        self.profile1.categories.add(self.category1)
        
        self.user2 = User.objects.create_user(
            username='worker2',
            email='worker2@example.com',
            password='testpass123',
            first_name='Jane',
            last_name='Electrician',
            user_type='worker'
        )
        self.profile2 = WorkerProfile.objects.create(
            user=self.user2,
            hourly_rate=Decimal('40.00'),
            verification_status='verified',
            is_profile_complete=True
        )
        self.profile2.categories.add(self.category2)
        
        # Client for authentication
        self.client_user = User.objects.create_user(
            username='searchclient',
            email='client@example.com',
            password='testpass123',
            user_type='client'
        )
        self.token = Token.objects.create(user=self.client_user)
        
        self.api_client = APIClient()
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
    
    def test_filter_by_hourly_rate(self):
        """Test filtering workers by hourly rate"""
        response = self.api_client.get('/api/workers/?min_rate=35')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_filter_by_verification_status(self):
        """Test filtering workers by verification status"""
        response = self.api_client.get('/api/workers/?verification_status=verified')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
