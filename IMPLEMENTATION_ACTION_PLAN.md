# IMPLEMENTATION ACTION PLAN
## Step-by-Step Guide to Fix Critical Gaps

---

## 🎯 OVERVIEW

This document provides detailed implementation steps for fixing the critical gaps identified in the mobile vs web platform analysis.

**Total Implementation Time**: 9-13 weeks  
**Critical Fixes**: 4-6 weeks  
**High Priority**: 3-4 weeks  
**Medium Priority**: 2-3 weeks

---

## 🔴 PHASE 1: CRITICAL FIXES (Weeks 1-6)

---

### 1. MOBILE: GDPR COMPLIANCE FEATURES

**Priority**: 🔴 CRITICAL (Legal requirement)  
**Estimated Effort**: 2-3 weeks  
**Developer**: Mobile team

#### Step 1.1: Data Export Feature (Week 1)

**Backend** (Already exists):
- ✅ API endpoint: `/api/v1/gdpr/export-my-data/`
- ✅ Returns complete user data JSON

**Mobile Tasks**:

1. **Create GDPR Settings Screen**
```typescript
// File: app/(client)/settings/gdpr.tsx
// File: app/(worker)/settings/gdpr.tsx

import { useState } from 'react';
import { Alert } from 'react-native';
import apiService from '../../../services/api';

// Create screen with:
// - Export Data button
// - Download progress indicator
// - Success/error handling
```

2. **Add API Service Methods**
```typescript
// File: services/api.ts

// Add these methods:
exportMyData: async () => {
  const response = await api.get('/api/v1/gdpr/export-my-data/');
  return response.data;
},

deletionPreview: async () => {
  const response = await api.get('/api/v1/gdpr/deletion-preview/');
  return response.data;
},

deleteAccount: async (confirm: boolean) => {
  const response = await api.post('/api/v1/gdpr/delete-account/', {
    confirm
  });
  return response.data;
},
```

3. **Implement Export Flow**
- Add "Export My Data" button
- Show loading spinner during export
- Save JSON to device storage
- Show success message with file location
- Handle errors gracefully

4. **Test Cases**
- [ ] Export generates complete JSON
- [ ] JSON includes all user data sections
- [ ] File saves to device successfully
- [ ] Works for both client and worker
- [ ] Error handling works

---

#### Step 1.2: Account Deletion Feature (Week 2)

**Mobile Tasks**:

1. **Create Deletion Preview Screen**
```typescript
// Show what will be deleted:
// - Personal information
// - Service requests / assignments
// - Messages
// - Documents
// - Payment history
// etc.
```

2. **Implement Deletion Flow**
- Show preview first
- Require explicit confirmation
- Use password verification
- Show "Are you sure?" dialog
- Process deletion
- Logout and clear local data
- Navigate to login screen

3. **Add Security Checks**
```typescript
// Before deletion:
// 1. Require current password
// 2. Show warning about irreversibility
// 3. Require typing "DELETE" to confirm
// 4. Final confirmation dialog
```

4. **Test Cases**
- [ ] Preview shows complete data list
- [ ] Confirmation flow works
- [ ] Password verification required
- [ ] Cannot be undone after confirmation
- [ ] Local data cleared
- [ ] User logged out
- [ ] Cannot login with deleted account

---

#### Step 1.3: Privacy Dashboard (Week 3)

1. **Create Privacy Dashboard**
```typescript
// File: app/(client)/settings/privacy-dashboard.tsx
// File: app/(worker)/settings/privacy-dashboard.tsx

Features:
- Data usage overview
- Privacy settings
- Download data button
- Delete account button
- Consent management
- Privacy policy link
- Terms of service link
```

2. **Add Navigation**
```typescript
// Update Settings menu to include:
// - Privacy & Data
//   - Download My Data
//   - Delete My Account
//   - Privacy Settings
//   - Privacy Policy
```

3. **Test Cases**
- [ ] Dashboard displays correctly
- [ ] All links work
- [ ] Settings persist
- [ ] GDPR compliant
- [ ] User-friendly

---

### 2. WEB: EDIT SERVICE REQUEST

**Priority**: 🔴 CRITICAL (Core functionality)  
**Estimated Effort**: 1-2 weeks  
**Developer**: Backend/Web team

#### Step 2.1: Backend Implementation (Week 1)

**Create Edit View**:

```python
# File: clients/views.py

@login_required
def edit_service_request(request, request_id):
    """Edit a pending service request"""
    service_request = get_object_or_404(
        ServiceRequest,
        id=request_id,
        client=request.user
    )
    
    # Only allow editing pending requests
    if service_request.status != 'pending':
        messages.error(request, 'You can only edit pending requests.')
        return redirect('clients:service_request_detail', request_id=request_id)
    
    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        location = request.POST.get('location', '').strip()
        city = request.POST.get('city', '').strip()
        urgency = request.POST.get('urgency', 'normal')
        client_notes = request.POST.get('client_notes', '').strip()
        
        # Duration and pricing
        duration_type = request.POST.get('duration_type')
        service_start_date = request.POST.get('service_start_date')
        service_end_date = request.POST.get('service_end_date')
        
        # Recalculate pricing
        daily_rate = float(service_request.category.daily_rate)
        duration_days = calculate_duration_days(
            duration_type, 
            service_start_date, 
            service_end_date
        )
        total_price = duration_days * daily_rate
        
        # Update service request
        service_request.title = title
        service_request.description = description
        service_request.location = location
        service_request.city = city
        service_request.urgency = urgency
        service_request.client_notes = client_notes
        service_request.duration_type = duration_type
        service_request.duration_days = duration_days
        service_request.total_price = total_price
        service_request.service_start_date = service_start_date
        service_request.service_end_date = service_end_date
        
        # CANNOT CHANGE: category, payment info
        
        service_request.save()
        
        messages.success(request, 'Service request updated successfully!')
        return redirect('clients:service_request_detail', request_id=request_id)
    
    context = {
        'service_request': service_request,
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'clients/edit_service_request.html', context)

def calculate_duration_days(duration_type, start_date, end_date):
    """Calculate duration days based on type"""
    if duration_type == 'daily':
        return 1
    elif duration_type == 'monthly':
        return 30
    elif duration_type == '3_months':
        return 90
    elif duration_type == '6_months':
        return 180
    elif duration_type == 'yearly':
        return 365
    elif duration_type == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        return (end - start).days + 1
    return 1
```

**Add URL Pattern**:

```python
# File: clients/urls.py

urlpatterns = [
    # ... existing patterns ...
    path('service-request/<int:request_id>/edit/', edit_service_request, name='edit_service_request'),
]
```

---

#### Step 2.2: Frontend Template (Week 2)

**Create Edit Template**:

```html
<!-- File: templates/clients/edit_service_request.html -->

{% extends 'clients/base_client.html' %}

{% block title %}Edit Service Request{% endblock %}

{% block content %}
<div class="container py-4">
    <div class="row">
        <div class="col-lg-8 mx-auto">
            <div class="card shadow-sm">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0">
                        <i class="bi bi-pencil-square me-2"></i>
                        Edit Service Request
                    </h4>
                </div>
                <div class="card-body">
                    <!-- Status Info -->
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle me-2"></i>
                        <strong>Note:</strong> You can only edit pending requests. 
                        Category and payment information cannot be changed.
                    </div>
                    
                    <form method="POST" id="editRequestForm">
                        {% csrf_token %}
                        
                        <!-- Category (Read-only) -->
                        <div class="mb-3">
                            <label class="form-label">Category</label>
                            <input type="text" class="form-control" 
                                   value="{{ service_request.category.name }}" 
                                   readonly disabled>
                            <small class="text-muted">
                                Category cannot be changed after creation
                            </small>
                        </div>
                        
                        <!-- Title -->
                        <div class="mb-3">
                            <label for="title" class="form-label">Title *</label>
                            <input type="text" class="form-control" 
                                   id="title" name="title" 
                                   value="{{ service_request.title }}" 
                                   required maxlength="200">
                        </div>
                        
                        <!-- Description -->
                        <div class="mb-3">
                            <label for="description" class="form-label">Description *</label>
                            <textarea class="form-control" id="description" 
                                      name="description" rows="5" 
                                      required>{{ service_request.description }}</textarea>
                        </div>
                        
                        <!-- Location -->
                        <div class="mb-3">
                            <label for="location" class="form-label">Location *</label>
                            <input type="text" class="form-control" 
                                   id="location" name="location" 
                                   value="{{ service_request.location }}" 
                                   required>
                        </div>
                        
                        <!-- City -->
                        <div class="mb-3">
                            <label for="city" class="form-label">City *</label>
                            <select class="form-select" id="city" name="city" required>
                                <option value="Dar es Salaam" {% if service_request.city == "Dar es Salaam" %}selected{% endif %}>Dar es Salaam</option>
                                <option value="Mwanza" {% if service_request.city == "Mwanza" %}selected{% endif %}>Mwanza</option>
                                <option value="Arusha" {% if service_request.city == "Arusha" %}selected{% endif %}>Arusha</option>
                                <!-- Add other cities -->
                            </select>
                        </div>
                        
                        <!-- Duration Type -->
                        <div class="mb-3">
                            <label for="duration_type" class="form-label">Duration Type *</label>
                            <select class="form-select" id="duration_type" 
                                    name="duration_type" required>
                                <option value="daily" {% if service_request.duration_type == "daily" %}selected{% endif %}>Daily (1 day)</option>
                                <option value="monthly" {% if service_request.duration_type == "monthly" %}selected{% endif %}>Monthly (30 days)</option>
                                <option value="3_months" {% if service_request.duration_type == "3_months" %}selected{% endif %}>3 Months (90 days)</option>
                                <option value="6_months" {% if service_request.duration_type == "6_months" %}selected{% endif %}>6 Months (180 days)</option>
                                <option value="yearly" {% if service_request.duration_type == "yearly" %}selected{% endif %}>Yearly (365 days)</option>
                                <option value="custom" {% if service_request.duration_type == "custom" %}selected{% endif %}>Custom Range</option>
                            </select>
                        </div>
                        
                        <!-- Custom Date Range (shown if custom selected) -->
                        <div id="customDateRange" style="display: {% if service_request.duration_type == 'custom' %}block{% else %}none{% endif %};">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label for="service_start_date" class="form-label">Start Date</label>
                                    <input type="date" class="form-control" 
                                           id="service_start_date" 
                                           name="service_start_date" 
                                           value="{{ service_request.service_start_date|date:'Y-m-d' }}">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label for="service_end_date" class="form-label">End Date</label>
                                    <input type="date" class="form-control" 
                                           id="service_end_date" 
                                           name="service_end_date" 
                                           value="{{ service_request.service_end_date|date:'Y-m-d' }}">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Urgency -->
                        <div class="mb-3">
                            <label for="urgency" class="form-label">Urgency</label>
                            <select class="form-select" id="urgency" name="urgency">
                                <option value="normal" {% if service_request.urgency == "normal" %}selected{% endif %}>Normal</option>
                                <option value="urgent" {% if service_request.urgency == "urgent" %}selected{% endif %}>Urgent</option>
                                <option value="emergency" {% if service_request.urgency == "emergency" %}selected{% endif %}>Emergency</option>
                            </select>
                        </div>
                        
                        <!-- Client Notes -->
                        <div class="mb-3">
                            <label for="client_notes" class="form-label">Additional Notes</label>
                            <textarea class="form-control" id="client_notes" 
                                      name="client_notes" 
                                      rows="3">{{ service_request.client_notes }}</textarea>
                        </div>
                        
                        <!-- Price Preview -->
                        <div class="alert alert-success">
                            <h5>Updated Price Preview</h5>
                            <p class="mb-0">
                                <strong id="pricePreview">
                                    TSH {{ service_request.total_price }}
                                </strong>
                                <br>
                                <small class="text-muted" id="priceBreakdown">
                                    {{ service_request.duration_days }} days × TSH {{ service_request.category.daily_rate }}/day
                                </small>
                            </p>
                        </div>
                        
                        <!-- Buttons -->
                        <div class="d-flex justify-content-between">
                            <a href="{% url 'clients:service_request_detail' service_request.id %}" 
                               class="btn btn-secondary">
                                <i class="bi bi-x-circle me-1"></i> Cancel
                            </a>
                            <button type="submit" class="btn btn-primary">
                                <i class="bi bi-save me-1"></i> Save Changes
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Show/hide custom date range
document.getElementById('duration_type').addEventListener('change', function() {
    const customDateRange = document.getElementById('customDateRange');
    if (this.value === 'custom') {
        customDateRange.style.display = 'block';
    } else {
        customDateRange.style.display = 'none';
    }
});

// Real-time price calculation (optional enhancement)
function updatePricePreview() {
    const durationType = document.getElementById('duration_type').value;
    const dailyRate = {{ service_request.category.daily_rate }};
    let durationDays = 1;
    
    // Calculate duration days based on type
    switch(durationType) {
        case 'daily': durationDays = 1; break;
        case 'monthly': durationDays = 30; break;
        case '3_months': durationDays = 90; break;
        case '6_months': durationDays = 180; break;
        case 'yearly': durationDays = 365; break;
        case 'custom':
            // Calculate from dates
            const startDate = new Date(document.getElementById('service_start_date').value);
            const endDate = new Date(document.getElementById('service_end_date').value);
            if (startDate && endDate && endDate >= startDate) {
                durationDays = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;
            }
            break;
    }
    
    const totalPrice = durationDays * dailyRate;
    document.getElementById('pricePreview').textContent = 'TSH ' + totalPrice.toFixed(2);
    document.getElementById('priceBreakdown').textContent = 
        durationDays + ' days × TSH ' + dailyRate.toFixed(2) + '/day';
}

// Add event listeners for price updates
document.getElementById('duration_type').addEventListener('change', updatePricePreview);
document.getElementById('service_start_date').addEventListener('change', updatePricePreview);
document.getElementById('service_end_date').addEventListener('change', updatePricePreview);
</script>
{% endblock %}
```

---

#### Step 2.3: Add Edit Button to Detail Page

**Update Service Request Detail Template**:

```html
<!-- File: templates/clients/service_request_detail.html -->

<!-- Add this button near the top of the page -->
{% if service_request.status == 'pending' %}
<div class="mb-3">
    <a href="{% url 'clients:edit_service_request' service_request.id %}" 
       class="btn btn-warning">
        <i class="bi bi-pencil-square me-1"></i> Edit Request
    </a>
</div>
{% endif %}
```

---

#### Step 2.4: Testing

**Test Cases**:
- [ ] Edit button only shows for pending requests
- [ ] Cannot edit after assignment
- [ ] Cannot edit after payment
- [ ] Cannot change category
- [ ] Can change title, description, location
- [ ] Can change duration and dates
- [ ] Price recalculates correctly
- [ ] Form validation works
- [ ] Success message displays
- [ ] Redirects to detail page
- [ ] Changes persist in database

---

### 3. WEB: WEBSOCKET REAL-TIME UPDATES

**Priority**: 🔴 CRITICAL (User experience)  
**Estimated Effort**: 3-4 weeks  
**Developer**: Backend team

#### Step 3.1: Install Django Channels (Week 3)

**Install Dependencies**:

```bash
pip install channels channels-redis daphne
```

**Update requirements.txt**:

```txt
# Add these lines
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0
redis==4.5.5
```

---

#### Step 3.2: Configure Django Channels (Week 3)

**Update settings.py**:

```python
# File: worker_connect/settings.py

# Add to INSTALLED_APPS
INSTALLED_APPS = [
    'daphne',  # Add at the top
    'channels',
    # ... existing apps ...
]

# ASGI configuration
ASGI_APPLICATION = 'worker_connect.asgi.application'

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

**Create ASGI file**:

```python
# File: worker_connect/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')

django_asgi_app = get_asgi_application()

from worker_connect.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

---

#### Step 3.3: Create WebSocket Consumer (Week 4)

**Create Consumer**:

```python
# File: worker_connect/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Create user-specific channel group
        self.group_name = f"user_{self.user.id}"
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong'
            }))
    
    # Receive message from group
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    async def message_update(self, event):
        """Send message update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))
    
    async def service_request_update(self, event):
        """Send service request update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'service_request_update',
            'data': event['data']
        }))
    
    async def payment_update(self, event):
        """Send payment update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'payment_update',
            'data': event['data']
        }))
```

**Create Routing**:

```python
# File: worker_connect/routing.py

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]
```

---

#### Step 3.4: Send Real-time Updates (Week 5)

**Create Helper Function**:

```python
# File: worker_connect/websocket_utils.py

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_notification_to_user(user_id, notification_data):
    """Send notification to specific user via WebSocket"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "notification_message",
            "notification": notification_data
        }
    )

def send_message_update(user_id, message_data):
    """Send message update to user"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "message_update",
            "message": message_data
        }
    )

def send_service_request_update(user_id, request_data):
    """Send service request update"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "service_request_update",
            "data": request_data
        }
    )

def send_payment_update(user_id, payment_data):
    """Send payment update"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "payment_update",
            "data": payment_data
        }
    )
```

**Use in Views** (Example):

```python
# File: admin_panel/views.py or service_requests/views.py

from worker_connect.websocket_utils import send_service_request_update


@staff_member_required
def assign_worker_to_request(request, request_id):
    # ... existing code ...
    
    # After successful assignment
    service_request.assigned_worker = worker
    service_request.status = 'assigned'
    service_request.save()
    
    # Send real-time update to client
    send_service_request_update(
        service_request.client.id,
        {
            'request_id': service_request.id,
            'status': 'assigned',
            'worker_name': worker.user.get_full_name()
        }
    )
    
    # Send notification to worker
    send_notification_to_user(
        worker.user.id,
        {
            'title': 'New Assignment',
            'message': f'You have been assigned to: {service_request.title}',
            'type': 'assignment'
        }
    )
    
    # ... rest of the code ...
```

---

#### Step 3.5: Frontend WebSocket Client (Week 6)

**Create WebSocket Handler**:

```html
<!-- File: templates/includes/websocket_handler.html -->

<script>
let ws = null;
let reconnectInterval = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function(e) {
        console.log('WebSocket connected');
        clearInterval(reconnectInterval);
        
        // Send ping every 30 seconds to keep connection alive
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        switch(data.type) {
            case 'notification':
                handleNotification(data.notification);
                break;
            case 'message':
                handleMessage(data.message);
                break;
            case 'service_request_update':
                handleServiceRequestUpdate(data.data);
                break;
            case 'payment_update':
                handlePaymentUpdate(data.data);
                break;
            case 'pong':
                // Keep-alive response
                break;
        }
    };
    
    ws.onclose = function(e) {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        reconnectInterval = setInterval(connectWebSocket, 5000);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        ws.close();
    };
}

function handleNotification(notification) {
    // Show browser notification
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(notification.title, {
            body: notification.message,
            icon: '/static/img/icon.png'
        });
    }
    
    // Update notification badge
    updateNotificationBadge();
    
    // Show in-app notification (toast)
    showToast(notification.title, notification.message);
}

function handleMessage(message) {
    // Update unread message count
    updateMessageBadge();
    
    // If on messages page, add new message to list
    if (window.location.pathname.includes('/messages/')) {
        addMessageToList(message);
    }
}

function handleServiceRequestUpdate(data) {
    // If on service request detail page, update status
    if (window.location.pathname.includes('/service-request/')) {
        updateServiceRequestStatus(data);
    }
    
    // Show notification
    showToast('Service Request Update', `Status: ${data.status}`);
}

function handlePaymentUpdate(data) {
    // Update payment status on page
    if (window.location.pathname.includes('/service-request/')) {
        updatePaymentStatus(data);
    }
}

function showToast(title, message) {
    // Create Bootstrap toast
    const toastHTML = `
        <div class="toast align-items-center text-white bg-primary border-0" 
             role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    const toastContainer = document.getElementById('toastContainer');
    if (toastContainer) {
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        const toast = new bootstrap.Toast(toastContainer.lastElementChild);
        toast.show();
    }
}

function updateNotificationBadge() {
    // Fetch new unread count and update badge
    fetch('/api/v1/notifications/unread-count/')
        .then(res => res.json())
        .then(data => {
            const badge = document.querySelector('.notification-badge');
            if (badge && data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'block';
            }
        });
}

function updateMessageBadge() {
    // Similar to updateNotificationBadge
    fetch('/api/v1/messages/unread-count/')
        .then(res => res.json())
        .then(data => {
            const badge = document.querySelector('.message-badge');
            if (badge && data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'block';
            }
        });
}

// Connect on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connectWebSocket);
} else {
    connectWebSocket();
}

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}
</script>

<!-- Toast Container -->
<div id="toastContainer" class="toast-container position-fixed bottom-0 end-0 p-3"></div>
```

**Include in Base Template**:

```html
<!-- File: templates/base.html -->

{% if user.is_authenticated %}
    {% include 'includes/websocket_handler.html' %}
{% endif %}
```

---

#### Step 3.6: Deploy with Daphne

**Update Deployment**:

```bash
# Instead of:
# gunicorn worker_connect.wsgi

# Use:
daphne -b 0.0.0.0 -p 8000 worker_connect.asgi:application
```

**Nginx Configuration**:

```nginx
# Add WebSocket support
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

---

#### Step 3.7: Testing

**Test Cases**:
- [ ] WebSocket connection establishes
- [ ] Connection survives page refresh
- [ ] Reconnects after disconnect
- [ ] Notifications arrive in real-time
- [ ] Messages arrive in real-time
- [ ] Status updates work
- [ ] Multiple tabs supported
- [ ] No memory leaks
- [ ] Works in production
- [ ] Redis running and connected

---

## 🟡 PHASE 2: HIGH PRIORITY (Weeks 7-10)

Continue in next document...

---

**Document**: Implementation Action Plan (Part 1)  
**Date**: March 8, 2026  
**Status**: Ready for implementation
