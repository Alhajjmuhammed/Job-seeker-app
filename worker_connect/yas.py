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
    """Compare two secrets without leaking their length by timing."""
    return bool(a) and bool(b) and hmac.compare_digest(str(a), str(b))


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
        logger.critical("Nothing identifies YAS - refusing the callback.")
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


def amount_shortfall(service_request, paid) -> Decimal:
    """How far short this payment falls. Zero or less means it covers it."""
    due = shillings_due(service_request)
    try:
        tolerance = Decimal(str(_setting("YAS_AMOUNT_TOLERANCE", "0")))
    except (InvalidOperation, ValueError):
        tolerance = Decimal("0")
    floor = due - (due * tolerance)
    return floor - Decimal(str(paid))


def _push_shortfall(service_request, amount_raw):
    """How far a push callback's Amount falls short. Returns (short, paid).

    An absent or unreadable Amount is treated as covering the booking,
    deliberately. We are the ones who named the amount when we asked for
    the prompt, so a callback that does not repeat it tells us nothing
    new - and refusing to credit a payment because a field we did not
    need was missing would take the client's money and give nothing back.
    """
    if amount_raw in (None, ""):
        return Decimal("0"), None
    try:
        paid = Decimal(str(amount_raw))
    except (InvalidOperation, ValueError):
        logger.warning("YAS push sent an Amount we cannot read: %r",
                       amount_raw)
        return Decimal("0"), None
    if not paid.is_finite() or paid <= 0 or paid > MOST_THEY_CAN_SEND:
        logger.warning("YAS push sent an implausible Amount: %r", amount_raw)
        return Decimal("0"), None
    return amount_shortfall(service_request, paid), paid


# ---------------------------------------------------------------------------
# Settling
# ---------------------------------------------------------------------------

def _record_transaction(service_request, receipt, amount):
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

    reference = str(receipt or "")[:64]
    if not reference:
        return None

    value = Decimal(str(amount or 0))
    taken = PaymentTransaction.objects.filter(
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
            )

    try:
        row = make(not taken)
    except Exception as exc:                                  # noqa: BLE001
        # A duplicate reference is the ordinary case here: the same
        # receipt arriving twice. Anything else is worth a line.
        logger.warning("YAS: could not record transaction %s for %s: %s",
                       reference, service_request.reference, exc)
        return None

    if taken:
        logger.info("YAS: recorded %s for %s unlinked - a demo reference "
                    "already holds that booking's slot.",
                    reference, service_request.reference)
    return row


def settle(service_request, receipt, amount=None) -> bool:
    """Mark it paid, once, and run the client's assign choice.

    Returns True when this call is what paid it, False when it was
    already paid - so a repeated callback is quiet rather than paying
    twice or notifying twice.

    Call inside atomic() with the row selected for update.
    """
    paid_now = service_request.mark_paid_by_gateway(receipt)
    if paid_now:
        _record_transaction(service_request, receipt,
                            amount if amount is not None
                            else service_request.total_price)
        logger.info("YAS settled service request %s with receipt %s",
                    service_request.reference, receipt)
    return paid_now


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

        logger.info("YAS ussd-push callback: %s", data)

        def first(keys):
            for k in keys:
                if data.get(k) not in (None, ""):
                    return data[k]
            return ""

        reference = str(first(PUSH_REF_KEYS))
        state = str(first(PUSH_STATUS_KEYS)).strip().lower()
        receipt = first(PUSH_TXN_KEYS)
        amount_raw = first(PUSH_AMOUNT_KEYS)

        found = request_for(reference)
        if found is None:
            # Answered as a success they can stop retrying: no amount of
            # retrying will conjure a request that does not exist, and a
            # failure makes their platform try for hours.
            logger.warning("YAS ussd-push callback for unknown reference %r",
                           reference)
            return self._reply(True, reference, "Reference not recognised")

        with transaction.atomic():
            locked = (ServiceRequest.objects.select_for_update()
                      .get(pk=found.pk))
            # Said twice is said once: a repeated callback must not pay
            # the request again or notify a second time.
            if locked.payment_status == "paid":
                return self._reply(True, reference, "Already settled")
            if state in GOOD:
                # Their Amount is mandatory and is what actually left the
                # client's wallet (spec 1 p.13), so it is checked. The
                # amount we asked for and the amount deducted should be
                # the same number; when they are not, something is wrong
                # on one side or the other and marking the booking paid
                # would hide it.
                short, paid = _push_shortfall(locked, amount_raw)
                if short > 0:
                    # Not marked paid, and not answered as a failure
                    # either: a failure makes their platform retry for
                    # hours, and retrying will not change the amount.
                    # Logged loudly instead, for a person to settle.
                    logger.critical(
                        "YAS push paid %s against %s due for %s - NOT "
                        "marked paid. Receipt %s. Refund or complete this "
                        "by hand.", paid, shillings_due(locked),
                        locked.reference, receipt)
                    return self._reply(True, reference,
                                       "Amount does not match the booking")
                settle(locked, receipt, amount=paid)
                return self._reply(True, reference)
            logger.info("YAS ussd-push declined for %s (%r)",
                        locked.reference, state)
            # Their payment failed; our handling of the news did not.
            return self._reply(True, reference, "Failure recorded")


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
                    txnid, reference, amount_raw, msisdn)

        found = request_for(reference)
        if found is None:
            return _xml_reply(txnid, reference, False, E_REF,
                              "No booking with that reference", msisdn)

        if found.payment_status == "paid":
            # Their platform may simply be asking again. Saying TS keeps
            # it from retrying for a request that is already settled.
            return _xml_reply(txnid, found.reference, True, OK,
                              "This booking is already paid", msisdn)

        # 'refunded' is the one state a payment must not be taken for:
        # the money has gone back, and taking it again would charge for
        # a booking nobody is going to do. A *failed* payment is left
        # payable on purpose - a mistyped PIN is the commonest reason
        # for one, and the client's next attempt should work.
        if found.payment_status == "refunded":
            logger.warning("YAS w2a for %s, which was refunded",
                           found.reference)
            return _xml_reply(txnid, found.reference, False, E_LOCKED,
                              "This booking was refunded and cannot be paid",
                              msisdn)

        try:
            paid = Decimal(str(amount_raw or "0"))
        except (InvalidOperation, ValueError):
            return _xml_reply(txnid, found.reference, False, E_AMOUNT,
                              "Amount not understood", msisdn)
        if not paid.is_finite() or paid <= 0:
            return _xml_reply(txnid, found.reference, False, E_AMOUNT,
                              "Amount must be more than zero", msisdn)
        # Decimal is happy to parse "1e999999" as a finite number, and a
        # number that large sails past the does-it-cover-the-booking
        # check and settles it. Their AMOUNT field is ten characters
        # (spec 2 p.5), so anything above ten digits is not an amount
        # they could have sent.
        if paid > MOST_THEY_CAN_SEND:
            logger.warning("YAS w2a implausible amount %r for %s",
                           amount_raw, found.reference)
            return _xml_reply(txnid, found.reference, False, E_TOO_HIGH,
                              "Amount is not a valid amount", msisdn)

        # Both sides are in shillings, so this is an exact comparison,
        # not the loose band a currency conversion would force.
        due = shillings_due(found)
        if due <= 0:
            logger.error("YAS w2a: service request %s has no price",
                         found.reference)
            return _xml_reply(txnid, found.reference, False, E_SERVICE,
                              "This booking has no amount set yet, "
                              "please try again shortly", msisdn)
        short = amount_shortfall(found, paid)
        if short > 0:
            logger.warning("YAS w2a short payment: %s against %s for %s",
                           paid, due, found.reference)
            return _xml_reply(
                txnid, found.reference, False, E_TOO_LOW,
                "Pay %s to confirm this booking" % due, msisdn)

        with transaction.atomic():
            locked = (ServiceRequest.objects.select_for_update()
                      .get(pk=found.pk))
            if locked.payment_status == "paid":
                return _xml_reply(txnid, locked.reference, True, OK,
                                  "This booking is already paid", msisdn)
            settle(locked, txnid, amount=paid)
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
