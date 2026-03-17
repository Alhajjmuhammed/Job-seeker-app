# Worker Display Fix - March 16, 2026

## Issue Reported
After a worker is assigned and accepts, the "Worker" column in `/services/client/my-requests/` was showing "Not assigned" instead of displaying the worker's name.

## Root Cause
The system now supports **multiple workers** per service request through the `ServiceRequestAssignment` model, but:

1. **View Issue**: The `client_web_my_requests` view was only loading the legacy `assigned_worker` field (single worker), not prefetching the new `assignments` relationship (multiple workers).

2. **Template Issue**: The template was only checking the legacy `assigned_worker` field, not the new `assignments` relationship.

## What Was Fixed

### 1. View Fix (`clients/service_request_web_views.py` - Line 194-200)

**BEFORE:**
```python
requests_list = ServiceRequest.objects.filter(
    client=request.user
).select_related('category', 'assigned_worker', 'assigned_worker__user').order_by('-created_at')
```

**AFTER:**
```python
requests_list = ServiceRequest.objects.filter(
    client=request.user
).select_related(
    'category', 
    'assigned_worker', 
    'assigned_worker__user'
).prefetch_related(
    'assignments__worker__user'  # Prefetch multiple worker assignments
).order_by('-created_at')
```

### 2. Template Fix (`templates/service_requests/client/my_requests.html` - Line 270-285)

**BEFORE:**
```django
<td>
    {% if request.assigned_worker %}
    <i class="bi bi-person-check text-success"></i>
    <span class="d-block">{{ request.assigned_worker.user.get_full_name }}</span>
    {% else %}
    <i class="bi bi-person-x text-muted"></i>
    <small class="text-muted">Not assigned</small>
    {% endif %}
</td>
```

**AFTER:**
```django
<td>
    {% with accepted_assignments=request.assignments.all %}
    {% if accepted_assignments %}
        {% for assignment in accepted_assignments %}
            {% if assignment.worker_accepted %}
            <i class="bi bi-person-check text-success"></i>
            <span class="d-block">{{ assignment.worker.user.get_full_name }}</span>
            {% if assignment.assignment_number > 1 or request.workers_needed > 1 %}
            <small class="badge bg-secondary">Worker #{{ assignment.assignment_number }}</small>
            {% endif %}
            {% elif assignment.status == 'pending' %}
            <i class="bi bi-hourglass-split text-warning"></i>
            <small class="text-muted d-block">{{ assignment.worker.user.get_full_name }}</small>
            <small class="badge bg-warning text-dark">Awaiting Response</small>
            {% endif %}
        {% endfor %}
    {% elif request.assigned_worker %}
        {% if request.worker_accepted %}
        <i class="bi bi-person-check text-success"></i>
        <span class="d-block">{{ request.assigned_worker.user.get_full_name }}</span>
        {% else %}
        <i class="bi bi-hourglass-split text-warning"></i>
        <small class="text-muted d-block">{{ request.assigned_worker.user.get_full_name }}</small>
        <small class="badge bg-warning text-dark">Awaiting Response</small>
        {% endif %}
    {% else %}
    <i class="bi bi-person-x text-muted"></i>
    <small class="text-muted">Not assigned</small>
    {% endif %}
    {% endwith %}
</td>
```

## How It Works Now

The Worker column will now display:

### Case 1: New Assignment System (Multiple Workers)
- ✅ **Worker Accepted**: Shows worker name with green checkmark icon
- ⏳ **Worker Pending**: Shows worker name with hourglass icon + "Awaiting Response" badge
- 👥 **Multiple Workers**: Shows all workers with "Worker #1", "Worker #2", etc. badges

### Case 2: Legacy System (Single Worker - Backward Compatibility)
- ✅ **Worker Accepted**: Shows worker name with green checkmark icon
- ⏳ **Worker Pending**: Shows worker name with hourglass icon + "Awaiting Response" badge

### Case 3: No Worker Assigned
- ❌ Shows "Not assigned" with person-x icon

## Status Indicators

| Status | Icon | Meaning |
|--------|------|---------|
| ✅ Green checkmark | `bi-person-check` | Worker has accepted the assignment |
| ⏳ Yellow hourglass | `bi-hourglass-split` | Worker assigned, awaiting their response |
| ❌ Gray person-x | `bi-person-x` | No worker assigned yet |

## Testing

1. **Refresh the page**: http://127.0.0.1:8080/services/client/my-requests/
2. **Check different scenarios**:
   - Requests with workers who accepted → Should show worker name with ✅
   - Requests with workers pending response → Should show name with ⏳
   - Requests with multiple workers → Should show all workers with badges
   - Unassigned requests → Should show "Not assigned"

## Benefits of This Fix

1. ✅ **Supports multiple workers** per service request
2. ✅ **Shows assignment status** (accepted vs pending)
3. ✅ **Backward compatible** with legacy single-worker system
4. ✅ **Clear visual indicators** for each state
5. ✅ **Worker numbering** for multi-worker requests

## Files Modified

1. `clients/service_request_web_views.py` - Added prefetch_related for assignments
2. `templates/service_requests/client/my_requests.html` - Updated Worker column logic

## Status

✅ **FIXED AND DEPLOYED** - Changes are live (server auto-reloaded at 12:42:06)
