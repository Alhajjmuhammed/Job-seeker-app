"""The Mixx by YAS endpoints a person reaches: clients paying, admins paying out.

worker_connect/yas.py answers YAS. worker_connect/yas_client.py calls
them. This module is the part of it our own apps and admin screen talk
to, and it does no protocol work of its own.

Everything here respects the two switches, and says so in words a person
can read rather than failing silently:

  ``YAS_CLIENT_PAYMENTS_ENABLED`` - a client may ask for the prompt
  ``YAS_WORKER_PAYOUTS_ENABLED``  - an admin may send a worker money

Both are off. The endpoints exist, answer, and explain that the method
is not available yet, which is what lets the admin screen that turns
them on be built against something real.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from clients.models import ClientRefund
from jobs.service_request_models import ServiceRequest
from worker_connect import yas_client
from worker_connect.pagination import StandardResultsSetPagination
from workers.models import WorkerPayout, WorkerProfile

# Named, not __name__: this and yas.py and yas_views.py all log to
# one trail, which is what gets compared against YAS's statement.
logger = logging.getLogger("worker_connect.yas")

OFF_FOR_CLIENTS = ("Paying by Mixx by Yas is not available yet. "
                   "Please use one of the other methods.")
OFF_FOR_PAYOUTS = "Paying workers by Mixx by Yas is not switched on."
OFF_FOR_REFUNDS = "Refunding by Mixx by Yas is not switched on."


def _payout_json(payout):
    return {
        "id": payout.id,
        "reference": payout.reference,
        "worker": {
            "id": payout.worker_id,
            "name": (payout.worker.user.get_full_name()
                     or payout.worker.user.username),
        },
        "service_request": payout.service_request_id,
        "amount": str(payout.amount),
        "phone_number": payout.phone_number,
        "state": payout.state,
        "state_label": payout.get_state_display(),
        "needs_a_person": payout.needs_a_person,
        "yas_status": payout.yas_status,
        "yas_message": payout.yas_message,
        "yas_txnid": payout.yas_txnid,
        "created_at": payout.created_at,
        "sent_at": payout.sent_at,
        "settled_at": payout.settled_at,
    }


# ---------------------------------------------------------------------------
# A client paying for their own booking
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_service_request(request, request_id):
    """Ask this client's phone for the money.

    POST /api/v1/payments/yas/pay/<request_id>/
    Body: {"phone_number": "0714123456"}   (optional - their own by default)

    A 200 here means the prompt is on its way, never that the booking is
    paid. The money arrives at the callback in yas.py, and only that
    marks anything paid.
    """
    service_request = get_object_or_404(ServiceRequest, pk=request_id)

    # A client may only pay their own booking. Without this, the id in
    # the URL is enough to make somebody else's prompt ring.
    if service_request.client_id != request.user.id and not request.user.is_staff:
        return Response({"error": "This booking is not yours."},
                        status=status.HTTP_404_NOT_FOUND)

    if service_request.payment_status == 'paid':
        return Response({"error": "This booking is already paid."},
                        status=status.HTTP_400_BAD_REQUEST)

    if not yas_client.client_payments_live():
        return Response({"error": OFF_FOR_CLIENTS},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    phone = (request.data.get('phone_number')
             or getattr(request.user, 'phone_number', '') or '')
    if not yas_client.msisdn(phone):
        return Response(
            {"error": "Enter the Mixx by Yas number to charge, "
                      "as 0714 123 456."},
            status=status.HTTP_400_BAD_REQUEST)

    # The reference has to exist before the request goes out, because it
    # is what comes home on the callback.
    reference = service_request.ensure_reference()

    sent, message = yas_client.request_payment(
        phone, service_request.total_price, reference,
        remarks="Worker Connect %s" % reference)

    if not sent:
        logger.warning("YAS would not take a payment for %s", reference)
        return Response(
            {"error": message or ("Mixx by Yas could not start the payment "
                                  "just now. Please try again shortly."),
             "reference": reference},
            status=status.HTTP_502_BAD_GATEWAY)

    return Response({
        "status": "prompt_sent",
        "message": message,
        "reference": reference,
        "amount": str(service_request.total_price),
        # Said plainly, because a client who closes the app here thinks
        # they have paid.
        "note": "The booking is confirmed once you approve the prompt "
                "on your phone.",
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_instructions(request, request_id):
    """What to type to pay this booking from the Mixx menu.

    GET /api/v1/payments/yas/instructions/<request_id>/

    This is the other way money arrives - the client pays from their own
    phone with no prompt from us - so it needs no switch: it is only
    telling them a reference. The reference is minted here if the
    booking has none, which is what makes the instructions true.
    """
    service_request = get_object_or_404(ServiceRequest, pk=request_id)
    if service_request.client_id != request.user.id and not request.user.is_staff:
        return Response({"error": "This booking is not yours."},
                        status=status.HTTP_404_NOT_FOUND)

    reference = service_request.ensure_reference()
    return Response({
        "reference": reference,
        "amount": str(service_request.total_price),
        "paid": service_request.payment_status == 'paid',
        "steps": [
            "Dial *150*01# on your Mixx by Yas line.",
            "Choose Pay Bills, then Enter Business Number.",
            "Enter the business number for Worker Connect.",
            "Enter %s as the reference." % reference,
            "Enter %s as the amount." % service_request.total_price,
            "Confirm with your PIN.",
        ],
    }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# An admin paying a worker
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def payouts(request):
    """List payouts, or create one.

    GET  /api/v1/payments/yas/payouts/?state=held
    POST /api/v1/payments/yas/payouts/
         {"worker_id": 12, "amount": "25000", "service_request_id": 48}

    Creating one sends nothing. It records what we intend to pay and to
    which number, and a second call sends it - so the amount and the
    destination are approved before any money moves.
    """
    if request.method == 'GET':
        rows = (WorkerPayout.objects
                .select_related('worker__user', 'service_request')
                .all())
        state = (request.query_params.get('state') or '').strip()
        if state:
            rows = rows.filter(state=state)
        worker_id = (request.query_params.get('worker_id') or '').strip()
        if worker_id.isdigit():
            rows = rows.filter(worker_id=int(worker_id))
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(rows, request)
        if page is None:
            body = {"count": rows.count(),
                    "results": [_payout_json(p) for p in rows]}
            answer = Response(body, status=status.HTTP_200_OK)
        else:
            answer = paginator.get_paginated_response(
                [_payout_json(p) for p in page])
        # The number an admin should act on today, kept separate from
        # the page because a held payout is the only kind that needs a
        # person, and it must not scroll off the first page.
        answer.data["held"] = WorkerPayout.objects.filter(
            state='held').count()
        return answer

    worker_id = request.data.get('worker_id')
    amount = request.data.get('amount')
    if not worker_id or amount in (None, ''):
        return Response({"error": "worker_id and amount are both required."},
                        status=status.HTTP_400_BAD_REQUEST)

    worker = WorkerProfile.objects.filter(pk=worker_id).first()
    if worker is None:
        return Response({"error": "No worker with that id."},
                        status=status.HTTP_404_NOT_FOUND)

    try:
        value = Decimal(str(amount))
        if not value.is_finite() or value <= 0:
            raise InvalidOperation
    except Exception:                                         # noqa: BLE001
        return Response({"error": "amount must be more than zero."},
                        status=status.HTTP_400_BAD_REQUEST)

    service_request = None
    request_id = request.data.get('service_request_id')
    if request_id:
        service_request = ServiceRequest.objects.filter(pk=request_id).first()
        if service_request is None:
            return Response({"error": "No booking with that id."},
                            status=status.HTTP_404_NOT_FOUND)

    payout = yas_client.create_payout(
        worker, value, created_by=request.user,
        service_request=service_request,
        phone_number=request.data.get('phone_number', ''))

    body = _payout_json(payout)
    if not yas_client.msisdn(payout.phone_number):
        # Said now rather than at send time, so an admin fixes the
        # number while they are still looking at the screen.
        body["warning"] = ("This worker has no usable Mixx by Yas number on "
                           "file. Add one before sending this payout.")
    return Response(body, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def send_payout(request, payout_id):
    """Send a payout that was already approved.

    POST /api/v1/payments/yas/payouts/<payout_id>/send/

    The reply's ``state`` is the whole answer. ``held`` is not a
    failure and not a success: Mixx by Yas did not tell us whether the
    money left, so somebody has to read the statement. Nothing retries
    a held payout on its own, and this endpoint will not send one.
    """
    payout = get_object_or_404(
        WorkerPayout.objects.select_related('worker__user'), pk=payout_id)

    if not yas_client.worker_payouts_live():
        return Response({"error": OFF_FOR_PAYOUTS,
                         "state": payout.state},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    state, message = yas_client.send_payout(payout)
    payout.refresh_from_db()

    body = _payout_json(payout)
    body["message"] = message
    if state == 'paid':
        code = status.HTTP_200_OK
    elif state == 'held':
        # 202: we accepted it and it is in flight as far as anyone
        # knows. Not a 200, because nothing has been confirmed.
        code = status.HTTP_202_ACCEPTED
    else:
        code = status.HTTP_400_BAD_REQUEST
    return Response(body, status=code)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def resolve_payout(request, payout_id):
    """Settle a held payout by hand, after reading the statement.

    POST /api/v1/payments/yas/payouts/<payout_id>/resolve/
         {"outcome": "paid" | "failed", "note": "seen on the 12 Nov statement"}

    Only a held payout can be resolved this way, and only a person can
    do it. That is the point: the gateway could not say what happened,
    so the record is corrected by somebody who looked.
    """
    payout = get_object_or_404(WorkerPayout, pk=payout_id)
    if payout.state != 'held':
        return Response(
            {"error": "Only a held payout is resolved by hand. This one is "
                      "%s." % payout.get_state_display(),
             "state": payout.state},
            status=status.HTTP_400_BAD_REQUEST)

    outcome = (request.data.get('outcome') or '').strip().lower()
    if outcome not in ('paid', 'failed'):
        return Response({"error": "outcome must be paid or failed."},
                        status=status.HTTP_400_BAD_REQUEST)

    note = str(request.data.get('note') or '').strip()
    who = request.user.get_full_name() or request.user.username
    with transaction.atomic():
        locked = WorkerPayout.objects.select_for_update().get(pk=payout.pk)
        if locked.state != 'held':
            return Response({"error": "Somebody else has just resolved this.",
                             "state": locked.state},
                            status=status.HTTP_409_CONFLICT)
        locked.state = outcome
        locked.yas_message = (
            "%s\nResolved by hand by %s%s"
            % (locked.yas_message, who, ": " + note if note else "")).strip()
        if outcome == 'paid':
            locked.settled_at = locked.settled_at or timezone.now()
        locked.save(update_fields=["state", "yas_message", "settled_at"])

    logger.info("Payout %s resolved as %s by %s", locked.reference,
                outcome, who)
    return Response(_payout_json(locked), status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# What the admin screen reads
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAdminUser])
def yas_status(request):
    """Is Mixx by Yas switched on, and if not, what is missing?

    GET /api/v1/payments/yas/status/

    This is what the admin screen for turning payments on reads. It
    never returns a credential - only whether each one is present - so
    it is safe on a screen and in a screenshot.
    """
    report = yas_client.status_report()
    report["payouts"] = {
        "held": WorkerPayout.objects.filter(state='held').count(),
        "pending": WorkerPayout.objects.filter(state='pending').count(),
        "sending": WorkerPayout.objects.filter(state='sending').count(),
    }
    report["refunds_waiting"] = {
        "held": ClientRefund.objects.filter(state='held').count(),
        "pending": ClientRefund.objects.filter(state='pending').count(),
        "sending": ClientRefund.objects.filter(state='sending').count(),
    }
    # The switches live in the environment, not the database, so say
    # where to change them rather than offering a button that cannot
    # work.
    report["how_to_switch_on"] = (
        "Set YAS_CLIENT_PAYMENTS_ENABLED, YAS_WORKER_PAYOUTS_ENABLED or "
        "YAS_REFUNDS_ENABLED to True in the server environment, then "
        "restart. Each needs the credentials above to be filled in first.")
    return Response(report, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# An admin sending a client their money back
# ---------------------------------------------------------------------------

def _refund_json(refund):
    return {
        "id": refund.id,
        "reference": refund.reference,
        "client": {
            "id": refund.client_id,
            "name": (refund.client.get_full_name() or refund.client.username),
        },
        "service_request": refund.service_request_id,
        "amount": str(refund.amount),
        "phone_number": refund.phone_number,
        "reason": refund.reason,
        "state": refund.state,
        "state_label": refund.get_state_display(),
        "needs_a_person": refund.needs_a_person,
        "mfs_transaction_id": refund.mfs_transaction_id,
        "purchase_reference": refund.purchase_reference,
        "yas_code": refund.yas_code,
        "yas_message": refund.yas_message,
        "yas_reference": refund.yas_reference,
        "created_at": refund.created_at,
        "sent_at": refund.sent_at,
        "settled_at": refund.settled_at,
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def refunds(request):
    """List refunds, or approve one.

    GET  /api/v1/payments/yas/refunds/?state=held
    POST /api/v1/payments/yas/refunds/
         {"service_request_id": 48, "amount": "30000",
          "reason": "paid 1000 against a 30000 booking"}

    Approving one sends nothing. A second call sends it, so the amount
    and the destination are agreed before money leaves.

    The amount defaults to what the booking cost and the destination to
    the client's own number, because the case this exists for is a
    client who paid the wrong amount and needs it back.
    """
    if request.method == 'GET':
        rows = (ClientRefund.objects
                .select_related('client', 'service_request').all())
        state = (request.query_params.get('state') or '').strip()
        if state:
            rows = rows.filter(state=state)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(rows, request)
        if page is None:
            answer = Response({"count": rows.count(),
                               "results": [_refund_json(r) for r in rows]},
                              status=status.HTTP_200_OK)
        else:
            answer = paginator.get_paginated_response(
                [_refund_json(r) for r in page])
        answer.data["held"] = ClientRefund.objects.filter(
            state='held').count()
        return answer

    request_id = request.data.get('service_request_id')
    if not request_id:
        return Response({"error": "service_request_id is required."},
                        status=status.HTTP_400_BAD_REQUEST)
    service_request = ServiceRequest.objects.filter(pk=request_id).first()
    if service_request is None:
        return Response({"error": "No booking with that id."},
                        status=status.HTTP_404_NOT_FOUND)

    amount = request.data.get('amount')
    if amount in (None, ''):
        amount = service_request.total_price
    try:
        value = Decimal(str(amount))
        if not value.is_finite() or value <= 0:
            raise InvalidOperation
    except Exception:                                         # noqa: BLE001
        return Response({"error": "amount must be more than zero."},
                        status=status.HTTP_400_BAD_REQUEST)

    phone = (request.data.get('phone_number')
             or getattr(service_request.client, 'phone_number', '') or '')

    refund = yas_client.create_refund(
        service_request, value, phone, created_by=request.user,
        reason=request.data.get('reason', ''),
        mfs_transaction_id=(request.data.get('mfs_transaction_id')
                            or service_request.payment_transaction_id or ''),
        purchase_reference=(request.data.get('purchase_reference')
                            or service_request.reference or ''))

    body = _refund_json(refund)
    if not yas_client.msisdn(refund.phone_number):
        body["warning"] = ("This client has no usable Mixx by Yas number on "
                           "file. Set phone_number on the refund before "
                           "sending it.")
    if not (refund.mfs_transaction_id or refund.purchase_reference):
        body["warning"] = ("This booking has neither a transaction id nor a "
                           "reference, so Mixx by Yas cannot find the "
                           "payment to reverse.")
    return Response(body, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def send_refund(request, refund_id):
    """Send a refund that was already approved.

    POST /api/v1/payments/yas/refunds/<refund_id>/send/

    As with a payout, ``held`` is neither a success nor a failure:
    Mixx by Yas did not say whether the money went, so a person reads
    the statement. Nothing retries a held refund on its own.
    """
    refund = get_object_or_404(
        ClientRefund.objects.select_related('client'), pk=refund_id)

    if not yas_client.refunds_live():
        return Response({"error": OFF_FOR_REFUNDS, "state": refund.state},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    state, message = yas_client.send_refund(refund)
    refund.refresh_from_db()

    body = _refund_json(refund)
    body["message"] = message
    if state == 'paid':
        code = status.HTTP_200_OK
    elif state == 'held':
        code = status.HTTP_202_ACCEPTED
    else:
        code = status.HTTP_400_BAD_REQUEST
    return Response(body, status=code)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def resolve_refund(request, refund_id):
    """Settle a held refund by hand, after reading the statement.

    POST /api/v1/payments/yas/refunds/<refund_id>/resolve/
         {"outcome": "paid" | "failed", "note": "seen on the statement"}
    """
    refund = get_object_or_404(ClientRefund, pk=refund_id)
    if refund.state != 'held':
        return Response(
            {"error": "Only a held refund is resolved by hand. This one is "
                      "%s." % refund.get_state_display(),
             "state": refund.state},
            status=status.HTTP_400_BAD_REQUEST)

    outcome = (request.data.get('outcome') or '').strip().lower()
    if outcome not in ('paid', 'failed'):
        return Response({"error": "outcome must be paid or failed."},
                        status=status.HTTP_400_BAD_REQUEST)

    note = str(request.data.get('note') or '').strip()
    who = request.user.get_full_name() or request.user.username
    with transaction.atomic():
        locked = ClientRefund.objects.select_for_update().get(pk=refund.pk)
        if locked.state != 'held':
            return Response({"error": "Somebody else has just resolved this.",
                             "state": locked.state},
                            status=status.HTTP_409_CONFLICT)
        locked.state = outcome
        locked.yas_message = (
            "%s\nResolved by hand by %s%s"
            % (locked.yas_message, who, ": " + note if note else "")).strip()
        if outcome == 'paid':
            locked.settled_at = locked.settled_at or timezone.now()
        locked.save(update_fields=["state", "yas_message", "settled_at"])

    logger.info("Refund %s resolved as %s by %s", locked.reference,
                outcome, who)
    return Response(_refund_json(locked), status=status.HTTP_200_OK)
