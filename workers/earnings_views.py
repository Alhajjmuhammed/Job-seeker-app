"""
Earnings API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from datetime import datetime

from workers.models import WorkerProfile
from .earnings import EarningsService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_summary(request):
    """
    Get earnings summary for the authenticated worker.
    
    Query params:
        - start_date: Start of period (YYYY-MM-DD)
        - end_date: End of period (YYYY-MM-DD)
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can access earnings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    start_date = None
    end_date = None
    
    start_str = request.query_params.get('start_date')
    end_str = request.query_params.get('end_date')
    
    if start_str:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
    if end_str:
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    
    summary = EarningsService.get_earnings_summary(worker, start_date, end_date)
    
    return Response(summary)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_breakdown(request):
    """
    Get earnings breakdown by time period.
    
    Query params:
        - group_by: 'day', 'week', or 'month' (default: month)
        - periods: Number of periods (default: 6)
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can access earnings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    group_by = request.query_params.get('group_by', 'month')
    periods = int(request.query_params.get('periods', 6))
    
    if group_by not in ['day', 'week', 'month']:
        return Response({
            'error': 'group_by must be day, week, or month'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    breakdown = EarningsService.get_earnings_breakdown(worker, group_by, periods)
    
    return Response({
        'group_by': group_by,
        'periods': periods,
        'breakdown': breakdown,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_by_category(request):
    """
    Get earnings breakdown by job category.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can access earnings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    categories = EarningsService.get_earnings_by_category(worker)
    
    return Response({
        'categories': categories,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_clients(request):
    """
    Get top clients by earnings.
    
    Query params:
        - limit: Maximum results (default: 10)
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can access earnings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    limit = int(request.query_params.get('limit', 10))
    
    clients = EarningsService.get_top_clients(worker, limit)
    
    return Response({
        'clients': clients,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tax_estimate(request):
    """
    Get estimated tax liability.
    
    Query params:
        - year: Tax year (default: current year)
        - rate: Tax rate as decimal (default: 0.25)
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can access earnings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    year = request.query_params.get('year')
    rate = request.query_params.get('rate', '0.25')
    
    from decimal import Decimal
    
    year = int(year) if year else None
    tax_rate = Decimal(rate)
    
    estimate = EarningsService.calculate_estimated_tax(worker, year, tax_rate)
    
    return Response(estimate)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    """
    Get payment history.
    
    Query params:
        - limit: Maximum results (default: 50)
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can access earnings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    limit = int(request.query_params.get('limit', 50))
    
    history = EarningsService.get_payment_history(worker, limit)
    
    return Response({
        'payments': history,
        'count': len(history),
    })
