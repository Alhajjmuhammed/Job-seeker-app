"""
Payment methods API URLs for Worker Connect.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .payment_methods_views import SavedCardViewSet, BankAccountViewSet, MobileMoneyAccountViewSet

router = DefaultRouter()
router.register(r'cards', SavedCardViewSet, basename='saved-card')
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-account')
router.register(r'mobile-money', MobileMoneyAccountViewSet, basename='mobile-money')

urlpatterns = [
    path('', include(router.urls)),
]
