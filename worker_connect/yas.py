"""Mixx by YAS - the two ways money arrives from that wallet.

The companion of worker_connect/yas_client.py. This module answers YAS
when they call us; that one calls them.

Written against the two specifications YAS issued:

  *Debit Mandate - TNZ, API Specification (Billers) v1.2* - the USSD
  push. JSON. We ask them to prompt a client's handset; they call our
  Biller Callback to say how it went. Their sample sends that callback
  as a **GET** with a JSON body, and expects a very particular JSON
  reply.

  *TIGOPESA Partner Integration API (A2W & W2A) v1.3*, use case 1 -
  the bill payment, which a client starts from the Mixx menu on their
  own phone with no help from us. **XML**, not JSON, in a ``<COMMAND>``
  envelope. One synchronous call does everything: they hand us the
  reference and the amount, we answer TS or TF with an error code and a
  line of text that is shown on the payer's own handset.

Neither caller can log in, so a shared secret stands in.

Two things worth saying plainly, because they are where this differs
from the same work on JamboGo:

  **A service request is priced in shillings already.** JamboGo prices
  in dollars and has to convert with an approximate rate, which forces
  a loose tolerance on the amount check. Here the price and the payment
  are the same currency, so the check is exact and a short payment is
  refused outright.

  **Settling has to run the client's assign choice.** A request that is
  marked paid without ``apply_assignment_mode`` sits with nobody
  assigned while the client waits for workers who were never asked.
  That is why settling goes through ``mark_paid_by_gateway`` rather
  than setting the fields here.

On the switches: ``YAS_CLIENT_PAYMENTS_ENABLED`` and
``YAS_WORKER_PAYOUTS_ENABLED`` gate what we *start* - asking a handset
for money, sending money to a worker. They deliberately do **not** gate
these two callbacks. Money that has already left a client's wallet must
be credited to their request whatever a flag says; refusing it would
take the payment and give nothing back. The callbacks are inert until
somebody configures credentials, because with nothing to identify YAS
by they refuse every caller.
"""
import base64
import binascii
import hmac
import logging
import re
import secrets
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from jobs.service_request_models import ServiceRequest

logger = logging.getLogger(__name__)

# --- what the Debit Mandate callback carries (spec 1, p.13) ----------------
PUSH_REF_KEYS = ("ReferenceID", "referenceId", "referenceID", "reference")
PUSH_STATUS_KEYS = ("Status", "status")
PUSH_TXN_KEYS = ("MFSTransactionID", "mfsTransactionId", "transactionId")
PUSH_AMOUNT_KEYS = ("Amount", "amount", "AMOUNT")
PUSH_DESC_KEYS = ("Description", "description")
PUSH_MSISDN_KEYS = ("CustomerMSISDN", "customerMSISDN", "customerMsisdn",
                    "MSISDN", "msisdn")

# Their own words for a payment that went through.
GOOD = {"true", "1", "success", "successful", "completed", "complete",
        "paid", "ok", "0", "00", "000", "200"}

# --- the SYNC_BILLPAY error codes YAS publish (spec 2, p.7) ---------------
OK = "error000"                  # Successful transaction
E_SERVICE = "error001"           # Service not available
E_REF = "error010"               # Invalid Customer Reference Number
E_LOCKED = "error011"            # Customer Reference Account locked
E_AMOUNT = "error012"            # Invalid Amount
E_SHORT = "error013"             # Amount insufficient
E_TOO_HIGH = "error014"          # Amount too high. Try a smaller amount
E_TOO_LOW = "error015"           # Amount too low. Try a larger amount
E_INVALID = "error016"           # Invalid payment
E_GENERAL = "error100"           # General Error

XML_CT = "text/xml; charset=utf-8"

# Their AMOUNT field is ten characters long (spec 2 p.5), so this is the
# largest sum that can honestly arrive. It is not a business limit - it is
# what stops a Decimal like "1e999999" being treated as money.
MOST_THEY_CAN_SEND = Decimal("9999999999")


def _setting(name, default=""):
    return getattr(settings, name, default)


def _same(a, b) -> bool:
    """Compare two secrets without leaking their length by timing.

    As UTF-8 bytes. hmac.compare_digest refuses a str holding anything
    outside ASCII with a TypeError, so a caller sending "café" as the
    secret used to turn a refusal into a 500.
    """
    if not (a and b):
        return False
    return hmac.compare_digest(str(a).encode("utf-8", "surrogatepass"),
                               str(b).encode("utf-8", "surrogatepass"))


def mask_msisdn(raw) -> str:
    """A phone number fit for a log: 2557*****678.

    The log is a copy, and a full list of who paid us from which number
    is not something a log file should be able to leak.
    """
    digits = "".join(c for c in str(raw or "") if c.isdigit())
    if not digits:
        return ""
    if len(digits) <= 7:
        return "*" * len(digits)
    return digits[:4] + "*" * (len(digits) - 7) + digits[-3:]


def _basic_ok(request) -> bool:
    """Did they authenticate with the biller username and password?

    YAS issue a biller username and password and have never said which
    way round they are used. If they authenticate to us with them and we
    only look for our own header, every real payment is refused - their
    money taken, ours credited to nobody - so both are accepted.
    """
    user = _setting("YAS_BILLER_USERNAME")
    password = _setting("YAS_BILLER_PASSWORD")
    if not (user and password):
        return False
    header = request.headers.get("Authorization") or ""
    if not header.lower().startswith("basic "):
        return False
    try:
        raw = base64.b64decode(header.split(None, 1)[1]).decode("utf-8")
    except (IndexError, ValueError, binascii.Error, UnicodeDecodeError):
        return False
    got_user, _, got_password = raw.partition(":")
    return _same(got_user, user) and _same(got_password, password)


def caller_ip(request) -> str:
    """Who is actually calling, from behind nginx.

    X-Real-IP is set by nginx from the socket it is answering, so a
    caller cannot put anything there. X-Forwarded-For is built with
    $proxy_add_x_forwarded_for, which *appends* to whatever arrived - so
    its leading entries are supplied by the caller and must never be
    trusted. Only its last entry was added by us, which is why that is
    the one read here.
    """
    real = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if real:
        return real
    chain = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if chain:
        return chain.split(",")[-1].strip()
    return (request.META.get("REMOTE_ADDR") or "").strip()


def from_allowed_ip(request) -> bool:
    """Did this come from YAS's gateway?

    Their biller callback carries no credential - see the
    specification: method GET, Content-Type, Cache-Control, and nothing
    else. So where it came from is the only thing that can vouch for it.

    YAS_ALLOWED_IPS is empty until somebody fills it in on purpose, and
    it must hold YAS's gateway address, never ours. Putting our own
    office address in it does not let us test anything; it opens the
    endpoint to whoever shares that address.
    """
    allowed = [a.strip() for a in
               str(_setting("YAS_ALLOWED_IPS")).split(",") if a.strip()]
    if not allowed:
        return False
    return caller_ip(request) in allowed


def secret_ok(request) -> bool:
    """Is this really YAS?

    Three ways in, because their two specifications do not agree on
    what we should expect:

      the shared secret in a header, which is what we ask them for;
      the biller username and password over HTTP Basic;
      or simply coming from their gateway's address - which is the only
      one the biller callback specification actually describes, since
      that request carries no credential at all.

    The last is why this cannot merely demand a secret: a callback we
    refuse is money YAS have already taken from a client and we have
    credited to nobody, and from the outside it would look like nothing
    happened at all.

    With nothing configured every call is refused rather than trusted.
    An open endpoint that marks requests paid is a way to get work done
    for free. Nothing here is ever logged - a log is a copy.
    """
    expected = _setting("YAS_CALLBACK_SECRET")
    has_basic = bool(_setting("YAS_BILLER_USERNAME")
                     and _setting("YAS_BILLER_PASSWORD"))
    has_ips = bool(str(_setting("YAS_ALLOWED_IPS")).strip())
    if not (expected or has_basic or has_ips):
        # WARNING, not CRITICAL: anybody on the internet can trigger this
        # line, and in production CRITICAL (anything from ERROR up) is
        # mailed to the admins - an open door to an e-mail flood. CRITICAL
        # is kept for real money anomalies.
        logger.warning("Nothing identifies YAS - refusing the callback.")
        return False
    got = (request.headers.get("X-YAS-Secret")
           or request.headers.get("X-Callback-Secret") or "")
    if expected and _same(got, expected):
        return True
    if _basic_ok(request):
        return True
    if from_allowed_ip(request):
        return True
    logger.warning("A YAS callback arrived from %s with nothing we accept.",
                   caller_ip(request) or "an unknown address")
    return False


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------

# What a client quotes when paying: "WC" and eight more characters. Taken
# from the model rather than written out again - two copies of a pattern
# is a pattern that gets changed in one place.
REQUEST_REF_RE = ServiceRequest.REFERENCE_RE


def request_ref_from(reference) -> str:
    """Our reference, out of whatever YAS send back.

    Spec 1 p.8: "This should be prefixed with the biller code". So what
    comes home is their code with ours after it, and the prefix has to
    come off before anything can be found.

    EasyFix has no biller code yet - the partnership is agreed, the
    integration is not - and a reference we cannot resolve is a payment
    taken from somebody and credited to nobody. So the prefix is
    stripped when it is configured, and when it is not, or when it is
    configured wrongly, our own reference is found inside whatever
    arrived instead. That works with no prefix, with a prefix we do not
    know, and with any separator between the two.
    """
    ref = str(reference or "").strip().upper()
    if not ref:
        return ""
    code = str(_setting("YAS_BILLER_CODE")).strip().upper()
    if code and ref.startswith(code):
        ref = ref[len(code):]
    ref = ref.lstrip("-_").strip()
    if REQUEST_REF_RE.fullmatch(ref):
        return ref
    found = REQUEST_REF_RE.search(ref)
    return found.group(0) if found else ref


def request_for(reference):
    """The service request a YAS reference points at, or None."""
    ref = request_ref_from(reference)
    if not ref:
        return None
    return ServiceRequest.objects.filter(reference=ref).first()


# ---------------------------------------------------------------------------
# Amounts
# ---------------------------------------------------------------------------

def shillings_due(service_request) -> Decimal:
    """What this request comes to, in whole shillings.

    No exchange rate is involved: a service request is priced in
    shillings and paid in shillings. Rounding is downward so a request
    priced at 750.40 is settled by a payment of 750 - YAS deal in whole
    shillings and cannot send the forty cents.
    """
    price = Decimal(str(getattr(service_request, "total_price", 0) or 0))
    return price.to_integral_value(rounding="ROUND_FLOOR")


def _tolerance() -> Decimal:
    """YAS_AMOUNT_TOLERANCE as a fraction in [0, 1). Anything else is 0.

    A typo in the environment must never quietly accept half payments.
    """
    try:
        tolerance = Decimal(str(_setting("YAS_AMOUNT_TOLERANCE", "0")))
    except (InvalidOperation, ValueError):
        return Decimal("0")
    if not tolerance.is_finite() or tolerance < 0 or tolerance >= 1:
        return Decimal("0")
    return tolerance


def amount_shortfall(service_request, paid) -> Decimal:
    """How far short this payment falls. Zero or less means it covers it."""
    due = shillings_due(service_request)
    floor = due - (due * _tolerance())
    return floor - Decimal(str(paid))


# What amount_verdict can say.
AMOUNT_OK = "ok"
AMOUNT_SHORT = "short"
AMOUNT_OVER = "over"
AMOUNT_NO_PRICE = "no_price"


def amount_verdict(service_request, paid) -> str:
    """Does this amount pay this booking? The one rule, used everywhere.

    Exact, in both directions. YAS_AMOUNT_TOLERANCE may allow a little
    LESS (a fee deducted on their side); nothing allows more. Money above
    the price is money we would have to send back, so it is refused (W2A)
    or left unapplied (push) rather than quietly kept.
    """
    due = shillings_due(service_request)
    if due <= 0:
        return AMOUNT_NO_PRICE
    paid = Decimal(str(paid))
    if paid > due:
        return AMOUNT_OVER
    if amount_shortfall(service_request, paid) > 0:
        return AMOUNT_SHORT
    return AMOUNT_OK


def parse_amount(raw):
    """A positive, finite, plausible Decimal, or None.

    None for anything absent, unreadable, zero, negative, not finite,
    larger than their AMOUNT field can hold, or not a scalar at all (a
    JSON list or object).
    """
    if raw is None or isinstance(raw, (bool, list, dict, tuple)):
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite() or value <= 0 or value > MOST_THEY_CAN_SEND:
        return None
    return value


# ---------------------------------------------------------------------------
# Settling
# ---------------------------------------------------------------------------

def receipt_key(receipt, gateway_reference="") -> str:
    """What a gateway payment is recorded under in PaymentTransaction.

    Their receipt (MFSTransactionID / TXNID) when they sent one. A
    callback without one still has to be recorded - and recognised when
    it is repeated - so it falls back to the ReferenceID it came with.
    """
    receipt = str(receipt or "").strip()
    if receipt:
        return receipt[:64]
    ref = str(gateway_reference or "").strip()
    return ("NORCPT-" + ref)[:64] if ref else ""


def _applied_here(service_request, key) -> bool:
    """Was this receipt the payment that paid this booking? (a genuine retry)"""
    from clients.models import PaymentTransaction

    if not key:
        return False
    if (service_request.payment_method == "Mixx by Yas"
            and service_request.payment_transaction_id
            and service_request.payment_transaction_id[:64] == key):
        return True
    return PaymentTransaction.objects.filter(
        reference=key, service_request=service_request,
        unapplied_reason="").exists()


def _recorded_here(service_request, key) -> bool:
    """Has this receipt already been recorded against this booking?"""
    from clients.models import PaymentTransaction

    if not key:
        return False
    return (_applied_here(service_request, key)
            or PaymentTransaction.objects.filter(
                reference=key, service_request=service_request).exists())


def receipt_used_elsewhere(service_request, key) -> bool:
    """Is this receipt already held by a different booking?

    One receipt is one payment, and one payment pays one booking. Without
    this a receipt replayed against a second reference settled that one
    too.
    """
    from clients.models import PaymentTransaction

    if not key:
        return False
    if (ServiceRequest.objects.filter(payment_transaction_id=key)
            .exclude(pk=service_request.pk).exists()):
        return True
    return (PaymentTransaction.objects.filter(reference=key)
            .exclude(service_request=service_request)
            .exclude(consumed_by=service_request).exists())


def record_unapplied(service_request, receipt, amount, gateway_reference,
                     reason, payer_msisdn="", amount_confirmed=True):
    """Money YAS took that we could not apply. Recorded, and shouted about.

    The row is what makes it refundable: a refund is only ever sent
    against a recorded payment, and capped at what that payment brought
    in. The CRITICAL line is what makes somebody look - in production it
    is mailed to the admins.
    """
    row = _record_transaction(service_request, receipt, amount,
                              gateway_reference=gateway_reference,
                              unapplied_reason=reason,
                              payer_msisdn=payer_msisdn,
                              amount_confirmed=amount_confirmed)
    logger.critical(
        "YAS took TSh %s for %s but it was NOT applied: %s. Receipt %s, "
        "reference %s, recorded as payment #%s. Refund or complete this by "
        "hand.", amount, service_request.reference, reason,
        receipt or "(none)", gateway_reference or "(none)",
        row.pk if row else "NOT RECORDED")
    return row


def _record_transaction(service_request, receipt, amount,
                        gateway_reference="", unapplied_reason="",
                        payer_msisdn="", amount_confirmed=True):
    """Leave a row an admin can look at. Never block a payment over it.

    consumed_by is a OneToOne and PaymentTransaction.consume claims one
    at booking time, so on any booking made through the app - which is
    all of them - that slot is already held by a demo reference. The
    real payment is then recorded unlinked rather than not at all: the
    money is what matters, and the booking's own
    payment_transaction_id carries the same receipt, so the two can
    still be put side by side.

    The demo row is deliberately left where it is. consume() claims
    rows by filtering consumed_by__isnull=True, so releasing one would
    make that reference claimable again and the same demo reference
    could be presented for a second booking.

    Nothing here is allowed to raise. By the time this runs the money
    has left the client's wallet and the booking is already paid.
    """
    from clients.models import PaymentTransaction

    reference = receipt_key(receipt, gateway_reference)
    if not reference:
        return None

    try:
        value = Decimal(str(amount if amount is not None else 0))
        if not value.is_finite():
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        value = Decimal("0")
    applied = not unapplied_reason
    # Only money that paid the booking may claim its consumed_by slot.
    taken = (not applied) or PaymentTransaction.objects.filter(
        consumed_by=service_request).exists()

    def make(link):
        with transaction.atomic():
            return PaymentTransaction.objects.create(
                reference=reference,
                client=service_request.client,
                amount=value,
                method="yas",
                is_demo=False,
                consumed_by=service_request if link else None,
                consumed_at=timezone.now(),
                service_request=service_request,
                gateway_reference=str(gateway_reference or "")[:64],
                unapplied_reason=str(unapplied_reason or ""),
                payer_msisdn=str(payer_msisdn or "")[:20],
                amount_confirmed=bool(amount_confirmed),
            )

    try:
        row = make(not taken)
    except Exception as exc:                                  # noqa: BLE001
        # A duplicate reference is the ordinary case here: the same
        # receipt arriving twice. Anything else is worth a line.
        logger.warning("YAS: could not record transaction %s for %s: %s",
                       reference, service_request.reference, exc)
        return None

    if taken and applied:
        logger.info("YAS: recorded %s for %s unlinked - a demo reference "
                    "already holds that booking's slot.",
                    reference, service_request.reference)
    return row


def settle(service_request, receipt, amount=None,
           gateway_reference="", payer_msisdn="") -> bool:
    """Mark it paid, once, and run the client's assign choice.

    Returns True when this call is what paid it, False when it could not
    (already paid by any route, refunded, or the job is closed) - so a
    repeated callback is quiet rather than paying twice or notifying
    twice. The callers check all of that first and record money they
    cannot apply; this refusing is the last line, not the first.

    Call inside atomic() with the row selected for update.
    """
    paid_now = service_request.mark_paid_by_gateway(receipt)
    if paid_now:
        _record_transaction(service_request, receipt,
                            amount if amount is not None
                            else service_request.total_price,
                            gateway_reference=gateway_reference,
                            payer_msisdn=payer_msisdn)
        logger.info("YAS settled service request %s with receipt %s",
                    service_request.reference, receipt)
    return paid_now


def _normal_msisdn(raw) -> str:
    """255 and nine digits, or "" - the one shape a refund can go to."""
    from worker_connect.yas_client import msisdn as _msisdn
    if isinstance(raw, (list, dict)):
        return ""
    return _msisdn(raw)


def _push_payer(service_request, reference, reported) -> str:
    """The wallet a push payment came from.

    The number YAS report on the callback when they report one;
    otherwise the number we prompted - but only when this callback
    answers that very prompt, so an older prompt's number is never
    borrowed.
    """
    number = _normal_msisdn(reported)
    if number:
        return number
    if (service_request.yas_prompt_reference
            and service_request.yas_prompt_reference.upper()
            == str(reference or "").upper()):
        return _normal_msisdn(service_request.yas_prompt_msisdn)
    return ""


def _closed_reason(service_request) -> str:
    """Why this booking cannot take money, or "" when it can."""
    if service_request.payment_status == "refunded":
        return "the booking was refunded"
    if service_request.status in ServiceRequest.CLOSED_STATUSES:
        return "the booking is %s" % service_request.status
    if service_request.is_paid:
        return "the booking is already paid"
    return ""


# ---------------------------------------------------------------------------
# 1. USSD push - the Biller Callback (spec 1, section 3)
# ---------------------------------------------------------------------------

@method_decorator(csrf_exempt, name="dispatch")
class YasUssdPushCallbackView(APIView):
    """How the prompt went.

    GET and POST both, because their sample says "Request Method: GET"
    with a JSON body while every other call in the document is a POST.
    A callback that arrives by the method we did not allow is a 405, and
    a 405 is what the live log showed on JamboGo before this was
    written there.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    # No throttle. The default AnonRateThrottle (100/hour) keys on the
    # caller's address, and every real callback comes from YAS's one
    # gateway: the 101st payment in an hour would be answered 429 and
    # its money credited to nobody. These views identify the caller
    # themselves (secret_ok) and do almost nothing for one they refuse.
    throttle_classes = []

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    # -- their reply shape (spec 1, p.15) ----------------------------------

    def _reply(self, ok_: bool, reference: str, description: str = ""):
        """The JSON they expect back.

        The success code appears twice in the specification with
        different values - BILLER-18-0000-S in the sample on page 15,
        BILLER-30-0000-S in the Expected Success Codes table below it.
        The table wins by default, and a setting changes it without a
        deploy, because this is the sort of thing only the first real
        test settles.
        """
        if ok_:
            code = _setting("YAS_CALLBACK_SUCCESS_CODE", "BILLER-30-0000-S")
            desc = description or "Callback successful"
        else:
            code = _setting("YAS_CALLBACK_FAILURE_CODE", "BILLER-30-3030-E")
            desc = description or "Callback failed"
        return Response({
            "ResponseCode": code,
            "ResponseStatus": bool(ok_),
            "ResponseDescription": desc,
            "ReferenceID": reference,
        }, status=status.HTTP_200_OK)

    def _handle(self, request):
        if not secret_ok(request):
            return Response({"status": "rejected"},
                            status=status.HTTP_401_UNAUTHORIZED)

        # A GET with a body is unusual enough that DRF may have parsed
        # neither; the query string is the other place it could be.
        #
        # request.data is read inside a try because reading it is what
        # parses the body: an empty body with a JSON content-type - which
        # is what a GET carrying its fields in the query string looks
        # like - makes DRF raise, and that raise becomes a 400 before the
        # query string is ever looked at. A payment lost to that would
        # look like nothing at all from the outside.
        data = {}
        try:
            body = request.data
        except Exception as exc:                              # noqa: BLE001
            logger.info("YAS ussd-push body would not parse (%s); "
                        "reading the query string instead.", exc)
            body = None
        if isinstance(body, dict):
            data.update(body)
        for k, v in request.query_params.items():
            data.setdefault(k, v)

        def first(keys):
            for k in keys:
                if data.get(k) not in (None, ""):
                    return data[k]
            return ""

        reference = str(first(PUSH_REF_KEYS)).strip()[:100]
        state = str(first(PUSH_STATUS_KEYS)).strip().lower()
        raw_receipt = first(PUSH_TXN_KEYS)
        receipt = ("" if isinstance(raw_receipt, (list, dict))
                   else str(raw_receipt or "").strip()[:64])
        amount_raw = first(PUSH_AMOUNT_KEYS)

        # Only the fields we act on. The whole body may carry the payer's
        # number and other things a log file has no business keeping.
        logger.info("YAS ussd-push callback: ref=%s status=%r receipt=%s "
                    "amount=%r", reference, state[:20], receipt,
                    str(amount_raw)[:20])

        found = request_for(reference)
        if found is None:
            # Answered as a success they can stop retrying: no amount of
            # retrying will conjure a request that does not exist, and a
            # failure makes their platform try for hours.
            if state in GOOD:
                logger.critical(
                    "YAS ussd-push says money was taken for unknown "
                    "reference %r (receipt %s, amount %r). Find it on the "
                    "statement and refund it by hand.", reference, receipt,
                    str(amount_raw)[:20])
            else:
                logger.warning("YAS ussd-push callback for unknown "
                               "reference %r", reference)
            return self._reply(True, reference, "Reference not recognised")

        with transaction.atomic():
            locked = (ServiceRequest.objects.select_for_update()
                      .get(pk=found.pk))

            if state not in GOOD:
                logger.info("YAS ussd-push declined for %s (%r)",
                            locked.reference, state[:20])
                # The prompt this answers is over, so the client may ask
                # for another straight away - but only when it is the
                # prompt we are waiting on, not an older one.
                if (locked.yas_prompt_sent_at
                        and (not locked.yas_prompt_reference
                             or locked.yas_prompt_reference.upper()
                             == reference.upper())):
                    locked.yas_prompt_sent_at = None
                    locked.save(update_fields=["yas_prompt_sent_at"])
                # Their payment failed; our handling of the news did not.
                return self._reply(True, reference, "Failure recorded")

            # From here on YAS say the money left the client's wallet.
            # Every way out either applies it to the booking or records
            # it as owed back - none of them drops it.
            key = receipt_key(receipt, reference)

            # Said twice is said once: a repeated callback must not pay
            # the request again, notify a second time or record twice.
            if _recorded_here(locked, key):
                return self._reply(True, reference, "Already settled")

            if receipt_used_elsewhere(locked, key):
                # The same receipt cannot pay two bookings. It is already
                # recorded where it first landed, so there is nothing new
                # to record here.
                logger.critical(
                    "YAS ussd-push for %s carries receipt %s, which is "
                    "already held by another booking - NOT applied. Check "
                    "the statement.", locked.reference, key)
                return self._reply(True, reference,
                                   "Receipt already used")

            payer = _push_payer(locked, reference, first(PUSH_MSISDN_KEYS))
            paid = parse_amount(amount_raw)
            closed = _closed_reason(locked)
            if closed:
                record_unapplied(locked, receipt,
                                 paid if paid is not None
                                 else shillings_due(locked),
                                 reference, closed, payer_msisdn=payer,
                                 amount_confirmed=paid is not None)
                return self._reply(True, reference,
                                   "Booking cannot take this payment")

            if paid is None:
                # Their Amount is mandatory (spec 1 p.13) and is what
                # actually left the wallet. Without a believable one we
                # cannot know the booking is covered, so it is not marked
                # paid. Recorded at the amount we asked for, which is the
                # best evidence we hold, for a person to check.
                # Flagged unconfirmed: not refundable until a person has
                # confirmed the real amount from the statement.
                record_unapplied(
                    locked, receipt, shillings_due(locked), reference,
                    "Amount missing or unreadable (%r); recorded at the "
                    "amount we asked for, UNCONFIRMED - check the statement"
                    % (str(amount_raw)[:20],), payer_msisdn=payer,
                    amount_confirmed=False)
                return self._reply(True, reference,
                                   "Amount does not match the booking")

            verdict = amount_verdict(locked, paid)
            if verdict != AMOUNT_OK:
                # Not marked paid, and not answered as a failure either:
                # a failure makes their platform retry for hours, and
                # retrying will not change the amount.
                record_unapplied(
                    locked, receipt, paid, reference,
                    "paid %s against %s due (%s)"
                    % (paid, shillings_due(locked), verdict),
                    payer_msisdn=payer)
                return self._reply(True, reference,
                                   "Amount does not match the booking")

            if not settle(locked, receipt, amount=paid,
                          gateway_reference=reference, payer_msisdn=payer):
                record_unapplied(locked, receipt, paid, reference,
                                 "the booking would not settle",
                                 payer_msisdn=payer)
                return self._reply(True, reference,
                                   "Booking cannot take this payment")
            return self._reply(True, reference)


# ---------------------------------------------------------------------------
# 2. W2A - SYNC_BILLPAY (spec 2, use case 1)
# ---------------------------------------------------------------------------

# The <COMMAND> envelope is flat: one level of single-valued tags, as
# every sample in the specification shows. Reading those tags with a
# pattern rather than an XML parser is deliberate - no parser means no
# entity expansion, so none of the attacks that come free with XML are
# available, and it keeps a dependency off a system that is already in
# use. Anything that does not match this shape is answered error100.
#
# ([^<]*) for the value, and not (.*?), is the whole correctness of this.
# A lazy dot-all value lets the outer <COMMAND> element match first and
# swallow everything inside it; findall then resumes after </COMMAND> and
# never sees a single field. A value that cannot contain a '<' cannot
# cross a tag boundary, so <COMMAND> simply does not match and the fields
# do. The first run of these tests caught exactly that, and as written it
# would have refused every real payment.
# The (?:prefix:)? groups let a namespaced envelope - <ns:COMMAND>,
# <ns:AMOUNT> - be read as AMOUNT. No sample YAS sent is
# namespaced, and defusedxml would have handled it without being
# asked; a pattern has to be told, and without this a namespaced
# envelope reads as no fields at all, which is a payment refused.
_TAG_RE = re.compile(
    r"<\s*(?:[A-Za-z_][\w.-]*:)?([A-Za-z_][\w.-]*)\s*[^>]*>"
    r"([^<]*)</\s*(?:[A-Za-z_][\w.-]*:)?\1\s*>")
# Is this a <COMMAND> envelope at all, namespace prefix or not?
# (?=[\s>/]) rather than \b so the word has to end here, and
# <COMMANDER> is not mistaken for an envelope.
_ENVELOPE_RE = re.compile(r"<\s*(?:[A-Za-z_][\w.-]*:)?COMMAND(?=[\s>/])",
                          re.IGNORECASE)
_ENTITIES = (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
             ("&apos;", "'"), ("&#39;", "'"), ("&amp;", "&"))


def _unescape(text: str) -> str:
    """Undo the five XML entities. &amp; last, or &amp;lt; becomes '<'."""
    for entity, char in _ENTITIES:
        text = text.replace(entity, char)
    return text


def read_command(raw: bytes):
    """The tags of a <COMMAND> envelope as a dict, or None if it is not one.

    Tag names come back upper-cased so a case difference on their side
    cannot lose a payment.
    """
    try:
        body = raw.decode("utf-8", "replace")
    except Exception:                                         # noqa: BLE001
        return None
    # A namespaced envelope is <ns:COMMAND>, so looking for "<COMMAND"
    # alone threw one out before the pattern ever ran.
    if not _ENVELOPE_RE.search(body):
        return None
    tags = {}
    for name, value in _TAG_RE.findall(body):
        upper = name.upper()
        if upper == "COMMAND":
            continue
        tags[upper] = _unescape(value).strip()
    return tags or None


def _xml_reply(txnid, refid, ok_, error_code, message, msisdn=""):
    """A SYNC_BILLPAY_RESPONSE, as spec 2 p.7 spells it.

    CONTENT is shown on the payer's own handset, so it says something a
    person can act on rather than an error number. ERRORDESC is left
    empty on success, as their own sample shows it - it describes what
    went wrong, and on a success nothing did.
    """
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<COMMAND>"
        "<TYPE>SYNC_BILLPAY_RESPONSE</TYPE>"
        "<TXNID>%s</TXNID>"
        "<REFID>%s</REFID>"
        "<RESULT>%s</RESULT>"
        "<ERRORCODE>%s</ERRORCODE>"
        "<ERRORDESC>%s</ERRORDESC>"
        "<MSISDN>%s</MSISDN>"
        "<FLAG>%s</FLAG>"
        "<CONTENT>%s</CONTENT>"
        "</COMMAND>"
    ) % (
        escape(str(txnid or "")), escape(str(refid or "")),
        "TS" if ok_ else "TF", escape(str(error_code or "")),
        "" if ok_ else escape(str(message or "")),
        escape(str(msisdn or "")),
        "Y" if ok_ else "N", escape(str(message or "")),
    )
    # HttpResponse, not DRF's Response: a renderer would wrap this in
    # JSON quotes and hand YAS a string where their parser wants a
    # document.
    return HttpResponse(body, status=status.HTTP_200_OK, content_type=XML_CT)


@method_decorator(csrf_exempt, name="dispatch")
class YasBillPaymentView(APIView):
    """A client paying from the Mixx menu on their own phone.

    One synchronous exchange: they give us the reference and the amount,
    we check both and answer TS or TF. There is no separate look-up step
    in this specification, so everything is decided here and the reason
    travels back in CONTENT for the payer to read on their handset.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    # No throttle - see YasUssdPushCallbackView.throttle_classes.
    throttle_classes = []
    # XML arrives as a body DRF has no parser for, so take it raw.
    parser_classes = []

    def post(self, request):
        if not secret_ok(request):
            return Response({"status": "rejected"},
                            status=status.HTTP_401_UNAUTHORIZED)

        raw = request.body or b""
        # A payment request is a few hundred bytes. Anything far larger
        # is not one.
        if len(raw) > 64 * 1024:
            logger.warning("YAS w2a body of %d bytes refused", len(raw))
            return _xml_reply("", "", False, E_GENERAL, "Request too large")

        tags = read_command(raw)
        if tags is None:
            logger.warning("YAS w2a sent something that is not a COMMAND")
            return _xml_reply("", "", False, E_GENERAL, "Malformed request")

        txnid = tags.get("TXNID", "")
        reference = (tags.get("CUSTOMERREFERENCEID")
                     or tags.get("REFERENCEID") or "")
        amount_raw = tags.get("AMOUNT", "")
        msisdn = tags.get("MSISDN", "")
        logger.info("YAS w2a: TXNID=%s ref=%s amount=%s msisdn=%s",
                    txnid, reference, amount_raw[:20], mask_msisdn(msisdn))

        found = request_for(reference)
        if found is None:
            return _xml_reply(txnid, reference, False, E_REF,
                              "No booking with that reference", msisdn)

        # A TS answer is what makes YAS take the money, and the TXNID is
        # the only thing that tells a retry of a payment we accepted from
        # a second payment. Without one we can neither tell nor refund.
        if not txnid:
            logger.warning("YAS w2a for %s arrived without a TXNID",
                           found.reference)
            return _xml_reply(txnid, found.reference, False, E_INVALID,
                              "Payment could not be identified", msisdn)

        # Everything is decided with the booking locked, so two payments
        # arriving together cannot both see it unpaid.
        with transaction.atomic():
            locked = (ServiceRequest.objects.select_for_update()
                      .get(pk=found.pk))
            key = receipt_key(txnid)

            # Their platform may simply be asking again about a payment we
            # already accepted. Only then is an already-paid booking
            # answered TS - TF to a genuine retry could make them reverse
            # money we have applied.
            if _applied_here(locked, key):
                return _xml_reply(txnid, locked.reference, True, OK,
                                  "This booking is already paid", msisdn)

            # One receipt pays one booking.
            if receipt_used_elsewhere(locked, key) or _recorded_here(locked,
                                                                     key):
                logger.warning("YAS w2a TXNID %s for %s was already used",
                               key, locked.reference)
                return _xml_reply(txnid, locked.reference, False, E_INVALID,
                                  "This payment was already used", msisdn)

            # Paid by any route (gateway, screenshot verified by an
            # admin...), refunded, cancelled or completed: TF, so YAS do
            # not take the money at all. A *failed* payment is left
            # payable on purpose - a mistyped PIN is the commonest reason
            # for one, and the client's next attempt should work.
            closed = _closed_reason(locked)
            if closed:
                logger.warning("YAS w2a for %s refused: %s",
                               locked.reference, closed)
                return _xml_reply(txnid, locked.reference, False, E_LOCKED,
                                  "This booking cannot be paid: %s"
                                  % closed.replace("the booking ", "it ", 1),
                                  msisdn)

            text = str(amount_raw or "").strip()
            try:
                paid = Decimal(text or "0")
            except (InvalidOperation, ValueError):
                return _xml_reply(txnid, locked.reference, False, E_AMOUNT,
                                  "Amount not understood", msisdn)
            if not paid.is_finite() or paid <= 0:
                return _xml_reply(txnid, locked.reference, False, E_AMOUNT,
                                  "Amount must be more than zero", msisdn)
            # Decimal is happy to parse "1e999999" as a finite number.
            # Their AMOUNT field is ten characters (spec 2 p.5), so
            # anything above ten digits is not an amount they could have
            # sent.
            if paid > MOST_THEY_CAN_SEND:
                logger.warning("YAS w2a implausible amount %r for %s",
                               text[:20], locked.reference)
                return _xml_reply(txnid, locked.reference, False, E_TOO_HIGH,
                                  "Amount is not a valid amount", msisdn)

            # Both sides are in shillings, so this is an exact comparison
            # in both directions - not the loose band a currency
            # conversion would force.
            due = shillings_due(locked)
            verdict = amount_verdict(locked, paid)
            if verdict == AMOUNT_NO_PRICE:
                logger.error("YAS w2a: service request %s has no price",
                             locked.reference)
                return _xml_reply(txnid, locked.reference, False, E_SERVICE,
                                  "This booking has no amount set yet, "
                                  "please try again shortly", msisdn)
            if verdict == AMOUNT_SHORT:
                logger.warning("YAS w2a short payment: %s against %s for %s",
                               paid, due, locked.reference)
                return _xml_reply(
                    txnid, locked.reference, False, E_TOO_LOW,
                    "Pay %s to confirm this booking" % due, msisdn)
            if verdict == AMOUNT_OVER:
                logger.warning("YAS w2a overpayment: %s against %s for %s",
                               paid, due, locked.reference)
                return _xml_reply(
                    txnid, locked.reference, False, E_TOO_HIGH,
                    "Pay exactly %s to confirm this booking" % due, msisdn)

            if not settle(locked, txnid, amount=paid,
                          gateway_reference=reference,
                          payer_msisdn=_normal_msisdn(msisdn)):
                return _xml_reply(txnid, locked.reference, False, E_LOCKED,
                                  "This booking cannot be paid", msisdn)
            reference_out = locked.reference

        return _xml_reply(
            txnid, reference_out, True, OK,
            "Payment received. Booking %s is confirmed." % reference_out,
            msisdn)


# ---------------------------------------------------------------------------
# Payout references
# ---------------------------------------------------------------------------

def new_refund_reference() -> str:
    """A ReferenceID for a refund: "RF" and eighteen digits.

    Twenty characters, matching the length of the sample reference in
    their specification. Random rather than counted, for the same
    reasons as a payout reference.
    """
    from clients.models import ClientRefund

    while True:
        ref = "RF" + "".join(secrets.choice("0123456789") for _ in range(18))
        if not ClientRefund.objects.filter(reference=ref).exists():
            return ref


def new_payout_reference() -> str:
    """A REFERENCEID for an A2W payout: "CI" and eighteen digits.

    Spec 2 p.5 gives the example CI000000000000000001 and notes the
    length as 20. Twenty characters exactly is what is sent, because a
    field with a stated length is the sort of thing a gateway truncates
    rather than complains about - and a truncated reference is a payout
    we cannot match to the worker it was for.

    Random rather than counted from the row id, so a reference can be
    minted before the row is saved and two servers can never pick the
    same one.
    """
    from workers.models import WorkerPayout

    while True:
        ref = "CI" + "".join(secrets.choice("0123456789") for _ in range(18))
        if not WorkerPayout.objects.filter(reference=ref).exists():
            return ref
