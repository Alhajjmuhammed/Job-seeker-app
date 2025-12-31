"""
Performance monitoring API views.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .performance import (
    PerformanceMetrics,
    get_system_metrics,
    get_database_metrics,
)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def performance_summary(request):
    """
    Get performance summary.
    
    Admin only.
    """
    metrics = PerformanceMetrics()
    
    return Response({
        'summary': metrics.get_summary(),
        'system': get_system_metrics(),
        'database': get_database_metrics(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def endpoint_stats(request):
    """
    Get per-endpoint performance statistics.
    
    Admin only.
    """
    metrics = PerformanceMetrics()
    
    stats = metrics.get_endpoint_stats()
    
    # Sort by count descending
    sorted_stats = dict(
        sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)
    )
    
    return Response({
        'endpoints': sorted_stats,
        'total_endpoints': len(sorted_stats),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def slow_queries(request):
    """
    Get recent slow database queries.
    
    Admin only.
    """
    metrics = PerformanceMetrics()
    limit = int(request.query_params.get('limit', 20))
    
    return Response({
        'queries': metrics.get_slow_queries(limit),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def recent_errors(request):
    """
    Get recent errors.
    
    Admin only.
    """
    metrics = PerformanceMetrics()
    limit = int(request.query_params.get('limit', 50))
    
    return Response({
        'errors': metrics.get_recent_errors(limit),
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_metrics(request):
    """
    Clear all performance metrics.
    
    Admin only.
    """
    metrics = PerformanceMetrics()
    metrics.clear()
    
    return Response({
        'success': True,
        'message': 'Performance metrics cleared'
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_health(request):
    """
    Get detailed system health information.
    
    Admin only.
    """
    system = get_system_metrics()
    
    # Determine health status
    health_status = 'healthy'
    warnings = []
    
    if 'error' not in system:
        if system.get('memory', {}).get('percent', 0) > 90:
            health_status = 'warning'
            warnings.append('High memory usage')
        
        if system.get('disk', {}).get('percent', 0) > 90:
            health_status = 'warning'
            warnings.append('Low disk space')
        
        if system.get('cpu_percent', 0) > 90:
            health_status = 'warning'
            warnings.append('High CPU usage')
    else:
        health_status = 'unknown'
    
    return Response({
        'status': health_status,
        'warnings': warnings,
        'metrics': system,
    })
