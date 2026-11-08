"""
App API for direct hire (a client books one worker straight away).
The rules live in jobs/direct_hire_service.py - shared with the website.

  POST /api/jobs/direct-hires/                 client books a worker
  GET  /api/jobs/direct-hires/?status=&role=   my bookings (newest first, paginated)
  GET  /api/jobs/direct-hires/<id>/            one booking (only the two sides)
  POST /api/jobs/direct-hires/<id>/complete/   client: done (+ rating 1-5, feedback)

Accept / decline / cancel stay at their existing paths (jobs/api_views.py).
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from worker_connect.pagination import paginate_queryset
from workers.models import WorkerProfile

from . import direct_hire_service as dh
from .forms import DirectHireRequestForm
from .models import DirectHireRequest

FIELDS = ('title', 'description', 'location', 'duration_type', 'duration_value', 'start_datetime', 'offered_rate')


def _err(e):
    return Response({'error': e.message, 'code': e.code}, status=e.status)


def _picture(request, worker):
    pic = getattr(worker, 'profile_image', None) or getattr(worker.user, 'profile_picture', None)
    if not pic:
        return None
    try:
        url = pic.url
    except ValueError:
        return None
    return request.build_absolute_uri(url) if request is not None else url


def hire_json(hire, user, request=None):
    """What one side of the booking may see. The address and the phones are
    shown to the worker only once they have accepted (like job addresses)."""
    is_worker = dh.is_worker_of(hire, user)
    is_client = hire.client_id == user.pk
    is_open = hire.status in dh.OPEN_STATES
    worker = hire.worker
    wu = worker.user
    busy = worker.availability == 'busy'
    show_location = is_client or is_open
    return {
        'id': hire.id,
        'my_role': 'worker' if is_worker else 'client' if is_client else None,
        'status': hire.status,
        'status_display': hire.get_status_display(),
        'title': hire.title,
        'description': hire.description,
        'location': hire.location if show_location else '',
        'location_hidden': not show_location,
        'duration_type': hire.duration_type,
        'duration_value': hire.duration_value,
        'duration_display': hire.duration_display,
        'start_datetime': hire.start_datetime.isoformat() if hire.start_datetime else None,
        'offered_rate': str(hire.offered_rate),
        'total_amount': str(hire.total_amount),
        'worker': {
            'id': worker.id,
            'user_id': wu.id,
            'full_name': wu.get_full_name() or wu.username,
            'rating': float(worker.average_rating or 0),
            'profile_picture': _picture(request, worker),
            'phone': (wu.phone_number or '') if (is_client and is_open) else '',
        },
        'client': {
            'id': hire.client_id,
            'full_name': hire.client.get_full_name() or hire.client.username,
            'phone': (hire.client.phone_number or '') if (is_worker and is_open) else '',
        },
        'worker_response_message': hire.worker_response_message,
        'responded_at': hire.responded_at.isoformat() if hire.responded_at else None,
        'completed_at': hire.completed_at.isoformat() if hire.completed_at else None,
        'client_rating': hire.client_rating,
        'client_feedback': hire.client_feedback,
        'created_at': hire.created_at.isoformat() if hire.created_at else None,
        # what the app may offer (the server checks again on every action)
        'worker_busy': bool(is_worker and hire.status == 'pending' and busy),
        'can_accept': bool(is_worker and hire.status == 'pending' and not busy),
        'can_decline': bool(is_worker and hire.status == 'pending'),
        'can_complete': bool(is_client and hire.status == 'accepted'),
        'can_cancel': hire.can_cancel(user),
        'can_chat': bool((is_worker or is_client) and is_open),
    }


class HireListSerializer:
    """Tiny adapter so paginate_queryset can serialise with hire_json."""

    def __init__(self, items, many=True, context=None):
        self.items = items
        self.context = context or {}

    @property
    def data(self):
        request = self.context.get('request')
        return [hire_json(h, request.user, request) for h in self.items]


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def direct_hires(request):
    if request.method == 'POST':
        return _create(request)
    role = request.query_params.get('role')
    if role not in ('client', 'worker'):
        role = None
    qs = dh.filter_status(dh.for_user(request.user, role), request.query_params.get('status'))
    return paginate_queryset(request, qs.order_by('-created_at', '-id'), HireListSerializer)


def _create(request):
    worker_id = request.data.get('worker_id') or request.data.get('worker')
    try:
        worker = WorkerProfile.objects.select_related('user').get(pk=int(worker_id))
    except (TypeError, ValueError, WorkerProfile.DoesNotExist):
        return Response({'error': 'Worker not found.', 'code': 'worker_not_found'}, status=status.HTTP_404_NOT_FOUND)
    try:
        dh.check_can_book(request.user, worker)
    except dh.DirectHireError as e:
        return _err(e)
    data = {k: request.data.get(k) for k in FIELDS if request.data.get(k) is not None}
    form = DirectHireRequestForm(data, suggested_rate=dh.suggested_rate(worker))
    if not form.is_valid():
        field, errors = next(iter(form.errors.items()))
        label = form.fields[field].label if field in form.fields else ''
        msg = str(errors[0])
        return Response({'error': f'{label}: {msg}' if label and field != '__all__' else msg,
                         'code': 'invalid', 'field': field,
                         'errors': {k: [str(x) for x in v] for k, v in form.errors.items()}},
                        status=status.HTTP_400_BAD_REQUEST)
    hire = dh.create(request.user, worker, form)
    return Response(hire_json(hire, request.user, request), status=status.HTTP_201_CREATED)


def _get_for(request, pk):
    hire = DirectHireRequest.objects.select_related('worker__user', 'client').filter(pk=pk).first()
    if hire is None or not dh.is_party(hire, request.user):
        return None
    return hire


NOT_FOUND = {'error': 'Booking not found.', 'code': 'not_found'}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def direct_hire_detail(request, pk):
    hire = _get_for(request, pk)
    if hire is None:
        return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
    return Response(hire_json(hire, request.user, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_direct_hire(request, pk):
    hire = _get_for(request, pk)
    if hire is None:
        return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
    try:
        dh.complete(hire, request.user, request.data.get('rating'), str(request.data.get('feedback') or '')[:2000])
    except dh.DirectHireError as e:
        return _err(e)
    hire = _get_for(request, pk)
    return Response(hire_json(hire, request.user, request))
