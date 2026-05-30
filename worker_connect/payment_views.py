"""
Payment API views for Worker Connect.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from workers.models import Payment, WorkerEarning
from .payments import PaymentService
from .payment_serializers import PaymentSerializer, WorkerEarningSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    """Payment management viewset"""
    
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter payments by user"""
        user = self.request.user
        
        # If client, show payments they made
        if hasattr(user, 'client_profile'):
            return Payment.objects.filter(client=user.client_profile)
        
        # If worker, show payments they received
        elif hasattr(user, 'worker_profile'):
            return Payment.objects.filter(worker=user.worker_profile)
        
        return Payment.objects.none()
    
    @action(detail=False, methods=['post'])
    def create_payment_intent(self, request):
        """Create a payment intent for a job"""
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            job_id = request.data.get('job_id')
            
            if amount <= 0:
                return Response(
                    {'error': 'Invalid amount'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get job and validate
            from jobs.models import JobRequest
            job = get_object_or_404(JobRequest, id=job_id)
            
            if not hasattr(request.user, 'client_profile'):
                return Response(
                    {'error': 'Only clients can create payments'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Initialize payment service
            PaymentService.initialize()
            
            if not PaymentService.is_available():
                return Response(
                    {'error': 'Payment service unavailable'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Create payment intent
            intent_data = PaymentService.create_payment_intent(
                amount=amount,
                metadata={
                    'job_id': str(job.id),
                    'client_id': str(request.user.client_profile.id)
                }
            )
            
            if not intent_data:
                return Response(
                    {'error': 'Failed to create payment intent'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Create payment record
            with transaction.atomic():
                payment = Payment.objects.create(
                    client=request.user.client_profile,
                    job=job,
                    amount=amount,
                    status='pending',
                    external_payment_id=intent_data['id'],
                    provider_data=intent_data
                )
            
            return Response({
                'success': True,
                'payment_id': str(payment.id),
                'client_secret': intent_data['client_secret'],
                'amount': str(amount)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """Confirm a payment"""
        payment = self.get_object()
        
        if payment.status != 'pending':
            return Response(
                {'error': 'Payment cannot be confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Confirm with payment provider
        result = PaymentService.confirm_payment(payment.external_payment_id)
        
        if result and result['status'] == 'succeeded':
            payment.status = 'held'  # Hold in escrow
            payment.save()
            
            return Response({
                'success': True,
                'status': 'held',
                'message': 'Payment held in escrow until job completion'
            })
        else:
            payment.status = 'failed'
            payment.save()
            
            return Response(
                {'error': 'Payment confirmation failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def release_escrow(self, request, pk=None):
        """Release escrow payment to worker (job completion)"""
        payment = self.get_object()
        
        if payment.status != 'held':
            return Response(
                {'error': 'Payment not in escrow'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Only client can release payment
        if payment.client != getattr(request.user, 'client_profile', None):
            return Response(
                {'error': 'Only the client can release payment'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Release payment
        with transaction.atomic():
            payment.status = 'completed'
            payment.save()
            
            # Record worker earning
            if payment.worker:
                WorkerEarning.objects.get_or_create(
                    worker=payment.worker,
                    job=payment.job,
                    payment=payment,
                    defaults={'amount': payment.worker_amount}
                )
        
        return Response({
            'success': True,
            'status': 'completed',
            'message': 'Payment released to worker'
        })
    
    @action(detail=False, methods=['get'])
    def earnings_summary(self, request):
        """Get earnings summary for worker"""
        if not hasattr(request.user, 'worker_profile'):
            return Response(
                {'error': 'Only workers can view earnings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        worker = request.user.worker_profile
        
        # Get completed payments
        completed_payments = Payment.objects.filter(
            worker=worker,
            status='completed'
        )
        
        total_earnings = sum(p.worker_amount for p in completed_payments)
        
        # Get pending payments
        pending_payments = Payment.objects.filter(
            worker=worker,
            status='held'
        )
        
        pending_earnings = sum(p.worker_amount for p in pending_payments)
        
        return Response({
            'total_earnings': str(total_earnings),
            'pending_earnings': str(pending_earnings),
            'completed_jobs': completed_payments.count(),
            'pending_jobs': pending_payments.count(),
        })


class WorkerEarningViewSet(viewsets.ReadOnlyModelViewSet):
    """Worker earnings viewset"""
    
    serializer_class = WorkerEarningSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter earnings by worker"""
        if hasattr(self.request.user, 'worker_profile'):
            return WorkerEarning.objects.filter(worker=self.request.user.worker_profile)
        return WorkerEarning.objects.none()