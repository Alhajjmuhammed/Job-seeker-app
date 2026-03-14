"""
Web views for Notification Center (Browser UI)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from worker_connect.notification_models import Notification


@login_required
def notification_center(request):
    """Display notification center page with list of notifications"""
    # Get all notifications for the user
    notifications_list = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    
    # Filter by read status if specified
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'unread':
        notifications_list = notifications_list.filter(is_read=False)
    elif status_filter == 'read':
        notifications_list = notifications_list.filter(is_read=True)
    
    # Filter by type if specified
    type_filter = request.GET.get('type')
    if type_filter:
        notifications_list = notifications_list.filter(notification_type=type_filter)
    
    # Pagination (20 per page)
    paginator = Paginator(notifications_list, 20)
    page = request.GET.get('page', 1)
    notifications = paginator.get_page(page)
    
    # Get counts for filters
    total_count = Notification.objects.filter(recipient=request.user).count()
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    # Determine base template based on user role
    base_template = 'base.html'
    if hasattr(request.user, 'worker_profile'):
        base_template = 'workers/base_worker.html'
    elif hasattr(request.user, 'client_profile'):
        base_template = 'clients/base_client.html'
    elif request.user.is_staff or request.user.is_superuser:
        base_template = 'admin_panel/base_admin.html'
    
    context = {
        'notifications': notifications,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'total_count': total_count,
        'unread_count': unread_count,
        'notification_types': Notification.NOTIFICATION_TYPES,
        'active_menu': 'notifications',
        'base_template': base_template,
    }
    
    return render(request, 'notifications/notification_center.html', context)


@login_required
def mark_notification_read_web(request, notification_id):
    """Mark a notification as read (web version)"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )
    
    notification.mark_as_read()
    
    # Return JSON if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    
    messages.success(request, 'Notification marked as read')
    return redirect('notification_center')


@login_required
def mark_all_read_web(request):
    """Mark all notifications as read (web version)"""
    if request.method == 'POST':
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        # Return JSON if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'count': updated,
                'message': f'Marked {updated} notifications as read'
            })
        
        messages.success(request, f'Marked {updated} notifications as read')
    
    return redirect('notification_center')


@login_required
def delete_notification_web(request, notification_id):
    """Delete a notification (web version)"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )
    
    if request.method == 'POST':
        notification.delete()
        
        # Return JSON if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Notification deleted'
            })
        
        messages.success(request, 'Notification deleted')
    
    return redirect('notification_center')


@login_required
def get_unread_count(request):
    """Get unread notification count (AJAX endpoint for navbar badge)"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'success': True,
        'count': count
    })
