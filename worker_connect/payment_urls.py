"""
Payment URLs for Worker Connect.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .payment_views import PaymentViewSet, WorkerEarningViewSet

app_name = 'payments'

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'earnings', WorkerEarningViewSet, basename='earning')

urlpatterns = [
    path('', include(router.urls)),
]