"""
Payment methods API views for Worker Connect.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from workers.models import SavedCard, BankAccount, MobileMoneyAccount
from .payment_serializers import SavedCardSerializer, BankAccountSerializer, MobileMoneyAccountSerializer
from .payments import PaymentService


class SavedCardViewSet(viewsets.ModelViewSet):
    """Saved card management viewset"""
    
    serializer_class = SavedCardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get user's saved cards"""
        return SavedCard.objects.filter(user=self.request.user, is_active=True)
    
    def create(self, request):
        """Add a new saved card"""
        try:
            # Initialize payment service
            PaymentService.initialize()
            
            if not PaymentService.is_available():
                return Response(
                    {'error': 'Payment service unavailable'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Get card token from request (should be created by Stripe.js on frontend)
            card_token = request.data.get('card_token')
            if not card_token:
                return Response(
                    {'error': 'Card token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create or get Stripe customer
            stripe_customer_id = request.data.get('stripe_customer_id')
            if not stripe_customer_id:
                # Create new Stripe customer
                customer_data = PaymentService.create_customer(
                    email=request.user.email,
                    metadata={'user_id': str(request.user.id)}
                )
                if not customer_data:
                    return Response(
                        {'error': 'Failed to create customer'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                stripe_customer_id = customer_data['id']
            
            # Attach card to customer
            card_data = PaymentService.attach_payment_method(
                customer_id=stripe_customer_id,
                payment_method_token=card_token
            )
            
            if not card_data:
                return Response(
                    {'error': 'Failed to attach card'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Extract card details from Stripe response
            card_info = card_data.get('card', {})
            
            # Create saved card record
            with transaction.atomic():
                saved_card = SavedCard.objects.create(
                    user=request.user,
                    card_type=card_info.get('brand', 'other').lower(),
                    last_four=card_info.get('last4', '0000'),
                    expiry_month=card_info.get('exp_month', 1),
                    expiry_year=card_info.get('exp_year', 2030),
                    cardholder_name=request.data.get('cardholder_name', request.user.get_full_name()),
                    stripe_card_id=card_data['id'],
                    stripe_customer_id=stripe_customer_id,
                    is_default=request.data.get('is_default', False)
                )
            
            serializer = self.get_serializer(saved_card)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """Remove a saved card"""
        try:
            card = self.get_object()
            
            # Detach card from Stripe
            PaymentService.initialize()
            if PaymentService.is_available():
                PaymentService.detach_payment_method(card.stripe_card_id)
            
            # Soft delete (mark as inactive)
            card.is_active = False
            card.save()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set a card as default"""
        card = self.get_object()
        card.is_default = True
        card.save()  # This will automatically unset other defaults
        
        serializer = self.get_serializer(card)
        return Response(serializer.data)


class BankAccountViewSet(viewsets.ModelViewSet):
    """Bank account management viewset (for workers)"""
    
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get user's bank accounts"""
        return BankAccount.objects.filter(user=self.request.user, is_active=True)
    
    def create(self, request):
        """Add a new bank account"""
        try:
            # Validate user is a worker
            if not hasattr(request.user, 'worker_profile'):
                return Response(
                    {'error': 'Only workers can add bank accounts'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Create bank account
            with transaction.atomic():
                bank_account = serializer.save(
                    user=request.user,
                    is_default=request.data.get('is_default', False)
                )
            
            return Response(
                self.get_serializer(bank_account).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """Remove a bank account"""
        try:
            bank_account = self.get_object()
            
            # Soft delete (mark as inactive)
            bank_account.is_active = False
            bank_account.save()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set a bank account as default"""
        bank_account = self.get_object()
        bank_account.is_default = True
        bank_account.save()  # This will automatically unset other defaults
        
        serializer = self.get_serializer(bank_account)
        return Response(serializer.data)


class MobileMoneyAccountViewSet(viewsets.ModelViewSet):
    """Mobile money account management viewset (for workers)"""
    
    serializer_class = MobileMoneyAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get user's mobile money accounts"""
        return MobileMoneyAccount.objects.filter(user=self.request.user, is_active=True)
    
    def create(self, request):
        """Add a new mobile money account"""
        try:
            # Validate user is a worker
            if not hasattr(request.user, 'worker_profile'):
                return Response(
                    {'error': 'Only workers can add mobile money accounts'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Create mobile money account
            with transaction.atomic():
                mobile_account = serializer.save(
                    user=request.user,
                    is_default=request.data.get('is_default', False)
                )
            
            return Response(
                self.get_serializer(mobile_account).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """Remove a mobile money account"""
        try:
            mobile_account = self.get_object()
            
            # Soft delete (mark as inactive)
            mobile_account.is_active = False
            mobile_account.save()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set a mobile money account as default"""
        mobile_account = self.get_object()
        mobile_account.is_default = True
        mobile_account.save()  # This will automatically unset other defaults
        
        serializer = self.get_serializer(mobile_account)
        return Response(serializer.data)
