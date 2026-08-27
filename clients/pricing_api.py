"""
Pricing and Payment API for Clients
"""
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone as django_timezone
from workers.models import Category
from jobs.service_request_models import ServiceRequest
from clients.models import PaymentTransaction

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_price(request):
    """
    Calculate price for service based on duration type and category
    
    POST /api/clients/calculate-price/
    Body: {
        "category_id": 1,
        "duration_type": "monthly",  # daily, monthly, 3_months, 6_months, yearly, custom
        "start_date": "2026-03-01",  # required for custom
        "end_date": "2026-03-15",    # required for custom
        "workers_needed": 2          # optional, defaults to 1
    }
    """
    try:
        category_id = request.data.get('category_id')
        duration_type = request.data.get('duration_type', 'daily')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        try:
            workers_needed = int(request.data.get('workers_needed', 1))
        except (TypeError, ValueError):
            return Response({
                'error': 'workers_needed must be a valid integer'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate workers_needed
        if workers_needed < 1:
            workers_needed = 1
        if workers_needed > 100:
            return Response({
                'error': 'Maximum 100 workers allowed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not category_id:
            return Response({
                'error': 'category_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get category and daily rate
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response({
                'error': 'Category not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        daily_rate = category.daily_rate
        
        # Calculate duration days
        duration_map = {
            'daily': 1,
            'monthly': 30,
            '3_months': 90,
            '6_months': 180,
            'yearly': 365,
        }
        
        if duration_type == 'custom':
            if not start_date or not end_date:
                return Response({
                    'error': 'start_date and end_date are required for custom duration'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if end < start:
                    return Response({
                        'error': 'end_date must be after start_date'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                duration_days = (end - start).days + 1  # +1 to include both days
            except ValueError:
                return Response({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            duration_days = duration_map.get(duration_type, 1)
        
        # Price per request: (category amount x workers) + one service fee.
        # duration_days is still returned so the client can show the schedule,
        # but it no longer affects the total. This quote comes from the same
        # model method the booking uses, so the two can never disagree.
        quote = ServiceRequest.quote(category, workers_needed)
        total_price = quote['total_price']

        return Response({
            'category_id': category.id,
            'category_name': category.name,
            'duration_type': duration_type,
            'duration_days': duration_days,
            'daily_rate': float(daily_rate),
            'amount_per_worker': float(quote['amount_per_worker']),
            'workers_needed': workers_needed,
            'service_fee': float(quote['service_fee']),
            'total_price': float(total_price),
            'currency': 'TSH',
            'start_date': start_date if duration_type == 'custom' else None,
            'end_date': end_date if duration_type == 'custom' else None,
        })
        
    except Exception as e:
        logger.error(f"Error calculating price: {str(e)}", exc_info=True)
        return Response({
            'error': 'Failed to calculate price'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_fake_payment(request):
    """
    Process fake payment for demo purposes (Card or M-Pesa)
    
    POST /api/v1/client/process-payment/
    Body for Card: {
        "amount": 750.00,
        "payment_type": "card",  # card or mpesa
        "card_number": "4242424242424242",  # or 5555555555555555 for Mastercard
        "card_holder": "John Doe",
        "card_expiry": "12/28",
        "card_cvv": "123"
    }
    
    Body for Mobile Money: {
        "amount": 750.00,
        "payment_type": "mpesa",
        "phone_number": "+255123456789"
    }
    
    DEMO MODE: Cards starting with 4242 (Visa) or 5555 (Mastercard), and phone numbers starting with +255 will succeed
    """
    try:
        amount = request.data.get('amount')
        payment_type = request.data.get('payment_type', 'card')  # card or mpesa
        
        if not amount:
            return Response({
                'error': 'amount is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return Response({
                    'error': 'amount must be greater than 0'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid amount format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate based on payment type
        if payment_type == 'card':
            card_number = request.data.get('card_number', '').replace(' ', '')
            card_holder = request.data.get('card_holder', '')
            card_expiry = request.data.get('card_expiry', '')
            card_cvv = request.data.get('card_cvv', '')
            
            if not all([card_number, card_holder, card_expiry, card_cvv]):
                return Response({
                    'error': 'Card details are incomplete'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Demo validation: Accept test cards (Visa 4242... or Mastercard 5555...)
            if not (card_number.startswith('4242') or card_number.startswith('5555')):
                return Response({
                    'success': False,
                    'error': 'Card declined. Use demo cards: 4242 4242 4242 4242 (Visa) or 5555 5555 5555 5555 (Mastercard)'
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
                
            payment_method = 'Credit Card'
            
        elif payment_type == 'mpesa':
            phone_number = request.data.get('phone_number', '')
            
            if not phone_number:
                return Response({
                    'error': 'Phone number is required for M-Pesa'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Demo validation: Accept numbers starting with +255
            if not phone_number.startswith('+255'):
                return Response({
                    'success': False,
                    'error': 'Invalid M-Pesa number. Use demo number: +255123456789'
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            payment_method = 'Mobile Money'
        else:
            return Response({
                'error': 'Invalid payment type. Use "card" or "mpesa"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Simulate payment processing delay
        import time
        time.sleep(2)  # Simulate network delay 
        
        # Generate fake transaction ID
        prefix = 'CARD' if payment_type == 'card' else 'MPESA'
        transaction_id = f"DEMO-{prefix}-{uuid.uuid4().hex[:12].upper()}"
        
        # 98% success rate for demo (using valid test credentials)
        import random
        success = random.random() < 0.98
        
        if success:
            # Record the reference we just issued. A booking can only be
            # marked paid by presenting a reference recorded here, to this
            # client, for this amount, and not already spent - otherwise any
            # made-up string was accepted as proof of payment.
            PaymentTransaction.objects.create(
                reference=transaction_id,
                client=request.user,
                amount=amount,
                method='card' if payment_type == 'card' else 'mpesa',
                is_demo=True,
            )
            return Response({
                'success': True,
                'transaction_id': transaction_id,
                'amount': float(amount),
                'currency': 'TSH',
                'payment_method': payment_method,
                'payment_type': payment_type,
                'status': 'paid',
                'paid_at': django_timezone.now().isoformat(),
                'message': f'Payment processed successfully via {payment_method} (DEMO MODE)'
            })
        else:
            return Response({
                'success': False,
                'error': f'{payment_method} payment failed. Please try again. (DEMO MODE)',
                'status': 'failed'
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Payment processing failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_category_pricing(request):
    """
    Get all categories with their pricing
    
    GET /api/clients/category-pricing/
    """
    try:
        categories = Category.objects.filter(is_active=True)
        
        pricing_data = []
        for category in categories:
            pricing_data.append({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'icon': category.icon,
                'daily_rate': float(category.daily_rate),
                'amount_per_worker': float(category.daily_rate),
                'service_fee': float(category.service_fee or 0),
                'currency': 'TSH',
                # Pricing is per request, so the duration a client picks does
                # not change the price. These examples show the effect of
                # crew size instead, which is what actually varies the total.
                'pricing_examples': {
                    '1_worker': float(category.price_for(1)),
                    '2_workers': float(category.price_for(2)),
                    '3_workers': float(category.price_for(3)),
                    '5_workers': float(category.price_for(5)),
                }
            })
        
        return Response({
            'categories': pricing_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching category pricing: {str(e)}", exc_info=True)
        return Response({
            'error': 'Failed to fetch category pricing'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
