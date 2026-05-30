"""
Payment integration foundation for Worker Connect.

Provides models and utilities for handling payments via Stripe.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

# Try to import Stripe (optional dependency)
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.info("Stripe not installed. Payment features disabled.")


class PaymentStatus:
    """Payment status constants."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (REFUNDED, 'Refunded'),
        (CANCELLED, 'Cancelled'),
    ]


class PaymentService:
    """
    Service for handling Stripe payments.
    """
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize Stripe with API key."""
        if cls._initialized or not STRIPE_AVAILABLE:
            return
        
        api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
        if api_key:
            stripe.api_key = api_key
            cls._initialized = True
            logger.info("Stripe initialized successfully")
        else:
            logger.warning("STRIPE_SECRET_KEY not set. Payments disabled.")
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if payment service is available."""
        return STRIPE_AVAILABLE and cls._initialized
    
    @classmethod
    def create_payment_intent(
        cls,
        amount: Decimal,
        currency: str = 'usd',
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe PaymentIntent.
        
        Args:
            amount: Amount in dollars (will be converted to cents)
            currency: Currency code (default: 'usd')
            customer_id: Optional Stripe customer ID
            metadata: Optional metadata dict
            
        Returns:
            PaymentIntent data or None if failed
        """
        if not cls.is_available():
            logger.warning("Stripe not available")
            return None
        
        try:
            # Convert to cents
            amount_cents = int(amount * 100)
            
            intent_data = {
                'amount': amount_cents,
                'currency': currency,
                'metadata': metadata or {},
            }
            
            if customer_id:
                intent_data['customer'] = customer_id
            
            intent = stripe.PaymentIntent.create(**intent_data)
            
            return {
                'id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount,
                'currency': currency,
                'status': intent.status,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return None
    
    @classmethod
    def confirm_payment(cls, payment_intent_id: str) -> Optional[Dict[str, Any]]:
        """
        Confirm a payment intent.
        
        Args:
            payment_intent_id: Stripe PaymentIntent ID
            
        Returns:
            Payment status data or None if failed
        """
        if not cls.is_available():
            return None
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'id': intent.id,
                'status': intent.status,
                'amount': Decimal(intent.amount) / 100,
                'currency': intent.currency,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return None
    
    @classmethod
    def create_customer(
        cls,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Create a Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Optional metadata
            
        Returns:
            Stripe customer ID or None if failed
        """
        if not cls.is_available():
            return None
        
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            return None
    
    @classmethod
    def create_refund(
        cls,
        payment_intent_id: str,
        amount: Optional[Decimal] = None,
        reason: str = 'requested_by_customer',
    ) -> Optional[Dict[str, Any]]:
        """
        Create a refund for a payment.
        
        Args:
            payment_intent_id: Stripe PaymentIntent ID
            amount: Optional partial refund amount (full refund if None)
            reason: Refund reason
            
        Returns:
            Refund data or None if failed
        """
        if not cls.is_available():
            return None
        
        try:
            refund_data = {
                'payment_intent': payment_intent_id,
                'reason': reason,
            }
            
            if amount is not None:
                refund_data['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_data)
            
            return {
                'id': refund.id,
                'amount': Decimal(refund.amount) / 100,
                'status': refund.status,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {e}")
            return None
    
    @classmethod
    def create_connected_account(cls, email: str, country: str = 'US') -> Optional[str]:
        """
        Create a Stripe Connect account for a worker to receive payments.
        
        Args:
            email: Worker email
            country: Country code
            
        Returns:
            Connected account ID or None if failed
        """
        if not cls.is_available():
            return None
        
        try:
            account = stripe.Account.create(
                type='express',
                email=email,
                country=country,
                capabilities={
                    'transfers': {'requested': True},
                },
            )
            return account.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Connect error: {e}")
            return None
    
    @classmethod
    def create_transfer(
        cls,
        amount: Decimal,
        destination_account_id: str,
        currency: str = 'usd',
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Transfer funds to a connected account (worker payout).
        
        Args:
            amount: Amount in dollars
            destination_account_id: Stripe connected account ID
            currency: Currency code
            metadata: Optional metadata
            
        Returns:
            Transfer data or None if failed
        """
        if not cls.is_available():
            return None
        
        try:
            transfer = stripe.Transfer.create(
                amount=int(amount * 100),
                currency=currency,
                destination=destination_account_id,
                metadata=metadata or {},
            )
            
            return {
                'id': transfer.id,
                'amount': Decimal(transfer.amount) / 100,
                'status': 'completed',
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe transfer error: {e}")
            return None


# Webhook handler
def handle_stripe_webhook(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
    """
    Handle incoming Stripe webhook events.
    
    Args:
        payload: Raw request body
        sig_header: Stripe signature header
        
    Returns:
        Event data or None if invalid
    """
    if not STRIPE_AVAILABLE:
        return None
    
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    if not endpoint_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not set")
        return None
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        
        # Handle specific event types
        if event.type == 'payment_intent.succeeded':
            logger.info(f"Payment succeeded: {event.data.object.id}")
            return {
                'type': 'payment_succeeded',
                'payment_intent_id': event.data.object.id,
                'amount': Decimal(event.data.object.amount) / 100,
            }
        
        elif event.type == 'payment_intent.payment_failed':
            logger.warning(f"Payment failed: {event.data.object.id}")
            return {
                'type': 'payment_failed',
                'payment_intent_id': event.data.object.id,
                'error': event.data.object.last_payment_error,
            }
        
        return {'type': event.type, 'data': event.data.object}
        
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe webhook signature")
        return None
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return None
