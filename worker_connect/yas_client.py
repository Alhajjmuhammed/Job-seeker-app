"""Calling Mixx by YAS - asking a client for money, sending a worker theirs.

The other half of worker_connect/yas.py. That one answers YAS when they
call us; this one calls them. Two directions, from two specifications:

  **Money in** - *Debit Mandate, v1.2*. A client taps pay in the app,
  their phone buzzes with a prompt, and they approve it there. A token
  first, then the payment request. The money does not arrive here - it
  arrives at the callback in yas.py, which is why nothing in this half
  marks anything paid.

  **Money out** - *Partner Integration (A2W & W2A), v1.3*, use case 2,
  which their document calls 'MFI CashIn'. XML in a ``<COMMAND>``
  envelope, synchronous: we send REQMFICI with the worker's number and
  the amount, and RESMFICI comes straight back saying whether it went.

Both switches are off until somebody turns them on:

  ``YAS_CLIENT_PAYMENTS_ENABLED`` - may we ask a client's phone for money
  ``YAS_WORKER_PAYOUTS_ENABLED``  - may we send money to a worker

Off means nothing is sent at all. That is deliberate: EasyFix has a
signed partnership with Mixx by Yas but no biller credentials yet, and
with a URL guessed rather than issued the kindest outcome is a timeout
and the unkindest is money moving somewhere nobody intended.

One hard-won note on URLs. These are settings holding **whole URLs**,
not a base address with a path appended. YAS give each partner its own
named routes on a shared gateway, and the paths printed in the
specifications belong to somebody else. On JamboGo, calling the printed
paths cost a day: one answered "Service Not Found" and the other sat for
thirty seconds before failing, because both are real routes for other
billers. Wait for YAS to name EasyFix's routes.
"""
import logging
import re
import secrets
import threading
import time
from decimal import Decimal
from xml.sax.saxutils import escape

# requests is not pinned in requirements.txt and was absent from this
# project's virtualenv when this was written. A plain import at the top
# of this module would raise at import time, and because yas_urls.py
# reaches this module, that would take down every URL on the site - not
# the payment feature, the whole site. So it is optional here, and
# nothing is ever considered configured without it.
try:
    import requests as http_requests
except ImportError:                                            # pragma: no cover
    http_requests = None

from django.conf import settings
from django.db import transaction
from django.utils import timezone

# Named, not __name__: this and yas.py and yas_views.py all log to
# one trail, which is what gets compared against YAS's statement.
logger = logging.getLogger("worker_connect.yas")


# A token lasts about an hour. Asking for a new one on every payment
# would be a second round trip for nothing, so it is kept until shortly
# before it expires - shortly, because a token that dies mid-request is
# a payment the client never sees.
_EXPIRY_MARGIN = 60
_token_lock = threading.Lock()
_token_cache = {"value": "", "expires_at": 0.0}


def _setting(name, default=""):
    return getattr(settings, name, default)


def _flag(name) -> bool:
    return bool(_setting(name, False))


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def msisdn(raw) -> str:
    """255 and nine digits, which is the only shape YAS accept (spec 1 p.8).

    People write their number every way there is - 0714..., +255 714...,
    with spaces and dashes. None of those are refused here; they are
    turned into the one form YAS read. Anything that is not a Tanzanian
    mobile number comes back empty, and an empty number is never sent.
    """
    digits = "".join(c for c in str(raw or "") if c.isdigit())
    if digits.startswith("255"):
        digits = digits[3:]
    elif digits.startswith("0"):
        digits = digits[1:]
    return "255" + digits if len(digits) == 9 and digits[0] in "67" else ""


def whole_shillings(amount) -> int:
    """YAS deal in whole shillings (spec 1 p.8, spec 2 p.5).

    A decimal here would be either refused or quietly rounded, and
    neither is ours to risk. Rounded down, so we never send a worker a
    shilling we did not owe and never ask a client for one.
    """
    return int(Decimal(str(amount or 0)).to_integral_value(
        rounding="ROUND_FLOOR"))


def can_call_out() -> bool:
    """Is the HTTP library we need actually installed?"""
    return http_requests is not None


def configured_for_payments() -> bool:
    """Is there enough here to ask a client's phone for money?"""
    return bool(can_call_out()
                and _setting("YAS_TOKEN_URL")
                and _setting("YAS_PAY_URL")
                and _setting("YAS_BILLER_USERNAME")
                and _setting("YAS_BILLER_PASSWORD")
                and _setting("YAS_BILLER_MSISDN"))


def configured_for_payouts() -> bool:
    """Is there enough here to send a worker money?"""
    return bool(can_call_out()
                and _setting("YAS_PAYOUT_URL")
                and _setting("YAS_DISBURSEMENT_MSISDN")
                and _setting("YAS_DISBURSEMENT_PIN"))


def client_payments_live() -> bool:
    return _flag("YAS_CLIENT_PAYMENTS_ENABLED") and configured_for_payments()


def worker_payouts_live() -> bool:
    return _flag("YAS_WORKER_PAYOUTS_ENABLED") and configured_for_payouts()


def status_report() -> dict:
    """What is switched on and what is still missing.

    This is what the admin screen reads, so it answers the two questions
    an admin actually has - can clients pay, can workers be paid - and
    then says which pieces are absent. It never returns a credential,
    only whether one is present.
    """
    pieces = {
        "http_library": can_call_out(),
        "token_url": bool(_setting("YAS_TOKEN_URL")),
        "pay_url": bool(_setting("YAS_PAY_URL")),
        "payout_url": bool(_setting("YAS_PAYOUT_URL")),
        "biller_code": bool(_setting("YAS_BILLER_CODE")),
        "biller_msisdn": bool(_setting("YAS_BILLER_MSISDN")),
        "biller_username": bool(_setting("YAS_BILLER_USERNAME")),
        "biller_password": bool(_setting("YAS_BILLER_PASSWORD")),
        "disbursement_msisdn": bool(_setting("YAS_DISBURSEMENT_MSISDN")),
        "disbursement_pin": bool(_setting("YAS_DISBURSEMENT_PIN")),
        "refund_url": bool(_setting("YAS_REFUND_URL")),
        "channel_msisdn": bool(_setting("YAS_CHANNEL_MSISDN")),
        "channel_pin": bool(_setting("YAS_CHANNEL_PIN")),
        "callback_identification": bool(
            _setting("YAS_CALLBACK_SECRET")
            or (_setting("YAS_BILLER_USERNAME")
                and _setting("YAS_BILLER_PASSWORD"))
            or str(_setting("YAS_ALLOWED_IPS")).strip()),
    }
    return {
        "client_payments": {
            "switched_on": _flag("YAS_CLIENT_PAYMENTS_ENABLED"),
            "configured": configured_for_payments(),
            "working": client_payments_live(),
        },
        "worker_payouts": {
            "switched_on": _flag("YAS_WORKER_PAYOUTS_ENABLED"),
            "configured": configured_for_payouts(),
            "working": worker_payouts_live(),
        },
        "refunds": {
            "switched_on": _flag("YAS_REFUNDS_ENABLED"),
            "configured": configured_for_refunds(),
            "working": refunds_live(),
        },
        "settings_present": pieces,
        "missing": sorted(k for k, present in pieces.items() if not present),
    }


# ---------------------------------------------------------------------------
# Money in: the Debit Mandate USSD push
# ---------------------------------------------------------------------------

def reference_for(request_ref: str, attempt_marker: str = "") -> str:
    """Our reference with the biller code in front, as they ask (spec 1 p.8).

    It comes home on the callback exactly like this, and yas.py finds
    ours inside it whatever the prefix turns out to be.

    attempt_marker is appended when one is given, which is how a second
    attempt at the same booking gets a reference YAS have not seen
    before. See new_attempt_marker for why that matters.
    """
    code = str(_setting("YAS_BILLER_CODE")).strip().upper()
    return (code + str(request_ref or "").strip().upper()
            + str(attempt_marker or ""))


def new_attempt_marker() -> str:
    """Digits that make one payment request distinguishable from the next.

    The specification calls ReferenceID "a unique reference ID, which
    can be used to track the request" (p.8) - unique per request, not
    per booking - and their own sample is the biller code followed by a
    timestamp: billercode20170724170909.

    Sending the booking reference unchanged on every attempt is why a
    client whose PIN fails cannot simply try again: YAS answer
    DuplicateRefID, and from the client's side it looks as though our
    site is broken. That is a fault still open on the other platform.

    Digits only, and appended rather than inserted, so the booking
    reference is still the first thing found inside whatever comes home
    on the callback.

    Microseconds, not seconds. Seconds with two random digits was the
    first attempt at this and it was not good enough: eight requests
    inside one second collide about a quarter of the time, which would
    produce the very DuplicateRefID this exists to avoid. The two
    random digits are still here, for two gunicorn workers landing on
    the same microsecond.

    YAS state no maximum for this field. The only reference length they
    put in writing anywhere is CUSTOMERREFERENCEID at 50 characters
    (Partner Integration p.5); the whole reference here comes to about
    35, so it sits inside that.
    """
    from django.utils import timezone as _tz

    return (_tz.now().strftime("%Y%m%d%H%M%S%f")
            + "".join(secrets.choice("0123456789") for _ in range(2)))


def _fetch_token() -> str:
    """A bearer token, or "" and a line in the log saying why."""
    url = str(_setting("YAS_TOKEN_URL"))
    try:
        resp = http_requests.post(
            url,
            data={
                "username": _setting("YAS_BILLER_USERNAME"),
                "password": _setting("YAS_BILLER_PASSWORD"),
                "grant_type": "password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Cache-Control": "no-cache"},
            timeout=20,
        )
        data = resp.json() if resp.content else {}
    except Exception as exc:                                   # noqa: BLE001
        logger.error("YAS token request failed: %s", exc)
        return ""
    if not isinstance(data, dict):
        logger.error("YAS token reply was not an object")
        return ""

    token_value = str(data.get("access_token") or "")
    if not token_value:
        # Their own error shape (spec 1 p.7). The password is never echoed.
        logger.error("YAS refused the token: %s - %s",
                     data.get("error"), data.get("error_description"))
        return ""
    try:
        lasts = int(data.get("expires_in") or 3599)
    except (TypeError, ValueError):
        lasts = 3599
    with _token_lock:
        _token_cache["value"] = token_value
        _token_cache["expires_at"] = time.time() + max(lasts - _EXPIRY_MARGIN,
                                                       30)
    logger.info("YAS token obtained, good for %ss", lasts)
    return token_value


def token() -> str:
    with _token_lock:
        if _token_cache["value"] and time.time() < _token_cache["expires_at"]:
            return _token_cache["value"]
    return _fetch_token()


def forget_token() -> None:
    """Drop the cached token, so the next call fetches a fresh one."""
    with _token_lock:
        _token_cache["value"] = ""
        _token_cache["expires_at"] = 0.0


def request_payment(phone, amount_tzs, request_ref, remarks="") -> tuple:
    """Ask a client's phone for the money. Returns (sent, message).

    ``sent`` means YAS accepted the request and the prompt is on its
    way, never that the money arrived - that is the callback's news, and
    treating acceptance as payment would confirm bookings nobody paid
    for.

    The message is for the client to read. It is empty when there is
    nothing useful to tell them, and the caller then says something
    about its own situation rather than putting words in YAS's mouth.
    """
    if not _flag("YAS_CLIENT_PAYMENTS_ENABLED"):
        return False, ""
    if not configured_for_payments():
        logger.warning("YAS client payments are on but not configured.")
        return False, ""

    number = msisdn(phone)
    if not number:
        return False, "That does not look like a Tanzanian mobile number."

    amount = whole_shillings(amount_tzs)
    if amount <= 0:
        return False, "There is nothing to pay on this booking."

    bearer = token()
    if not bearer:
        return False, ""

    body = {
        "CustomerMSISDN": number,
        # Ours, as YAS hold it - sent exactly as they gave it. On
        # JamboGo they listed it with eleven digits where a Tanzanian
        # number has twelve, and listed it that way twice, so it is what
        # their system contains rather than a slip. The payer's own
        # number is checked above because they type it; this one is
        # configuration from the people who issued it, and refusing it
        # on our own arithmetic would block every payment over a digit
        # we cannot see.
        "BillerMSISDN": (msisdn(_setting("YAS_BILLER_MSISDN"))
                         or str(_setting("YAS_BILLER_MSISDN")).strip()),
        "Amount": amount,
        "Remarks": (remarks or "Worker Connect booking %s" % request_ref)[:100],
        # Unique per attempt, not per booking - see new_attempt_marker.
        "ReferenceID": reference_for(request_ref, new_attempt_marker()),
    }
    headers = {
        "Authorization": "bearer " + bearer,
        # The username and password again, as their own headers,
        # alongside the bearer token. Unusual enough to be worth saying
        # out loud; it is what the specification shows (p.8-10).
        "Username": str(_setting("YAS_BILLER_USERNAME")),
        "Password": str(_setting("YAS_BILLER_PASSWORD")),
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    url = str(_setting("YAS_PAY_URL"))

    def send():
        resp = http_requests.post(url, json=body, headers=headers, timeout=30)
        payload = {}
        if resp.content:
            try:
                payload = resp.json()
            except ValueError:
                payload = {}
        return resp, (payload if isinstance(payload, dict) else {})

    try:
        resp, data = send()
        # A token can expire between being cached and being used. One
        # retry with a fresh one, rather than losing the payment to a
        # second of bad luck.
        if resp.status_code in (401, 403):
            forget_token()
            bearer = token()
            if bearer:
                headers["Authorization"] = "bearer " + bearer
                resp, data = send()
    except Exception as exc:                                   # noqa: BLE001
        logger.error("YAS payment request failed for %s: %s", request_ref, exc)
        return False, ""

    accepted = bool(data.get("ResponseStatus") is True
                    or str(data.get("ResponseStatus")).lower() == "true")
    # The headers carry a password, so only the verdict is logged.
    logger.info("YAS BillerPay for %s -> http=%s code=%s status=%s",
                request_ref, resp.status_code, data.get("ResponseCode"),
                data.get("ResponseStatus"))
    if not accepted:
        logger.warning("YAS would not take the payment for %s: %s",
                       request_ref, data.get("ResponseDescription"))
        return False, ""
    return True, ("Check your phone. Approve the Mixx by Yas request to "
                  "confirm your booking.")


# ---------------------------------------------------------------------------
# Money out: A2W, 'MFI CashIn' (spec 2, use case 2)
# ---------------------------------------------------------------------------

# Spec 2 p.9. 200 and 0 are the only successes. 100, and any timeout,
# mean we were not told - the money may have gone. Everything else is a
# refusal we can act on.
PAYOUT_OK = {"200", "0", "00"}
PAYOUT_UNKNOWN = {"100"}

# Their published failures, in words a person can act on. Anything not
# in here is reported with YAS's own text.
PAYOUT_REASONS = {
    "00026": "The disbursement account PIN has expired and needs changing.",
    "00031": "More than the network allows in one transfer.",
    "00042": "The amount is not a multiple the network accepts.",
    "317": "The worker's wallet is barred.",
    "410": "More than the maximum allowed in one transfer.",
    "2117": "Our disbursement account is barred.",
    "60014": "Our account has reached its daily limit.",
    "60017": "Less than the smallest transfer allowed.",
    "60018": "More than the maximum allowed.",
    "60019": "Our disbursement account would go below its minimum balance.",
    "60021": "The worker has reached their daily number of transactions.",
    "60024": "The daily limit for transfers has been reached.",
    "60028": "More than the worker's wallet accepts in one transfer.",
    "60030": "The worker's wallet would go over its maximum balance.",
    "60074": "The worker's wallet is not set up to receive this transfer.",
}

# ([^<]*), not (.*?) - see the note on _TAG_RE in yas.py. A dot-all
# value lets <COMMAND> swallow its own children and the envelope parses
# to nothing, which here would read every successful payout as unknown.
# The (?:prefix:)? groups let a namespaced envelope - <ns:COMMAND>,
# <ns:AMOUNT> - be read as AMOUNT. No sample YAS sent is
# namespaced, and defusedxml would have handled it without being
# asked; a pattern has to be told, and without this a namespaced
# envelope reads as no fields at all, which is a payment refused.
_PAYOUT_TAG_RE = re.compile(
    r"<\s*(?:[A-Za-z_][\w.-]*:)?([A-Za-z_][\w.-]*)\s*[^>]*>"
    r"([^<]*)</\s*(?:[A-Za-z_][\w.-]*:)?\1\s*>")


def _read_response(raw: str) -> dict:
    """The tags of a RESMFICI envelope. Flat and single-valued, as p.8 shows.

    Read with a pattern rather than an XML parser on purpose: no parser
    means no entity expansion, and it keeps a dependency off a system
    that is already carrying real work.
    """
    out = {}
    for name, value in _PAYOUT_TAG_RE.findall(raw or ""):
        upper = name.upper()
        if upper == "COMMAND":
            continue
        out[upper] = value.strip()
    return out


def _payout_envelope(payout) -> str:
    """REQMFICI, as spec 2 p.5 spells it.

    SENDERNAME and BRAND_ID were added in v1.3 - the first is shown to
    the worker so they know who paid them, the second is the numeric
    brand id YAS issue at integration.
    """
    fields = (
        ("TYPE", "REQMFICI"),
        ("REFERENCEID", payout.reference),
        ("MSISDN", (msisdn(_setting("YAS_DISBURSEMENT_MSISDN"))
                    or str(_setting("YAS_DISBURSEMENT_MSISDN")).strip())),
        ("PIN", str(_setting("YAS_DISBURSEMENT_PIN")).strip()),
        ("MSISDN1", msisdn(payout.phone_number)),
        ("AMOUNT", str(whole_shillings(payout.amount))),
        ("SENDERNAME", str(_setting("YAS_SENDER_NAME", "Worker Connect"))[:50]),
        ("BRAND_ID", str(_setting("YAS_BRAND_ID")).strip()),
        ("LANGUAGE1", "en"),
    )
    inner = "".join("<%s>%s</%s>" % (tag, escape(value), tag)
                    for tag, value in fields)
    return '<?xml version="1.0"?><COMMAND>%s</COMMAND>' % inner


def send_payout(payout) -> tuple:
    """Send a worker their money. Returns (state, message).

    The state is written to the row before this returns, and it is the
    row - not this return value - that decides whether anybody may try
    again.

    The order of what happens here is the whole point of the function:

      the row is moved to 'sending' and committed *before* the call. If
      this process dies mid-request, the row does not read 'pending',
      because a pending row invites a second payout for money that may
      already have left;

      a timeout, a dropped connection or TXNSTATUS 100 lands on 'held',
      which the specification asks for in so many words (p.9): we were
      not told whether the money moved, so a person checks the statement
      and decides. Nothing automatic retries a held payout;

      only 200 or 0 is 'paid'.
    """
    from workers.models import WorkerPayout

    if not _flag("YAS_WORKER_PAYOUTS_ENABLED"):
        return payout.state, "Paying workers by Mixx by Yas is not switched on."
    if not configured_for_payouts():
        logger.warning("YAS worker payouts are on but not configured.")
        return payout.state, ("Mixx by Yas payouts are switched on but not "
                              "set up yet.")

    number = msisdn(payout.phone_number)
    if not number:
        return payout.state, ("The worker's number is not a Tanzanian mobile "
                              "number.")
    amount = whole_shillings(payout.amount)
    if amount <= 0:
        return payout.state, "There is nothing to send."

    # Claim the row. Only a pending payout may be sent, and the claim is
    # a conditional update so two admins pressing at once cannot both
    # win: whichever one changes no rows stops here.
    claimed = (WorkerPayout.objects
               .filter(pk=payout.pk, state='pending')
               .update(state='sending', sent_at=timezone.now()))
    if not claimed:
        payout.refresh_from_db()
        return payout.state, {
            'sending': "This payout is already on its way.",
            'paid': "This payout has already been paid.",
            'held': ("This payout is held - check the Mixx by Yas statement "
                     "before sending it again."),
            'failed': "This payout failed. Create a new one to try again.",
        }.get(payout.state, "This payout cannot be sent.")
    payout.refresh_from_db()

    def finish(state, yas_status="", message="", txnid=""):
        payout.state = state
        payout.yas_status = str(yas_status or "")[:10]
        payout.yas_message = str(message or "")
        payout.yas_txnid = str(txnid or "")[:40]
        if state == 'paid':
            payout.settled_at = timezone.now()
        payout.save(update_fields=["state", "yas_status", "yas_message",
                                   "yas_txnid", "settled_at"])
        return state, message

    body = _payout_envelope(payout)
    headers = {"Content-Type": "text/xml; charset=utf-8",
               "Cache-Control": "no-cache",
               "Connection": "keep-alive"}
    # What, if anything, goes in Authorization is for YAS to say at
    # integration; the specification names the envelope's PIN as the
    # credential. A setting rather than a guess, so it can be filled in
    # without a deploy.
    auth = str(_setting("YAS_PAYOUT_AUTH")).strip()
    if auth:
        headers["Authorization"] = auth

    try:
        resp = http_requests.post(str(_setting("YAS_PAYOUT_URL")),
                                  data=body.encode("utf-8"),
                                  headers=headers, timeout=60)
        text = resp.text or ""
    except Exception as exc:                                   # noqa: BLE001
        # "This is the same case for any kind of timeout as well" - p.9.
        logger.error("YAS payout %s: no answer (%s). Held.",
                     payout.reference, exc)
        return finish('held', "", (
            "Mixx by Yas did not answer, so whether the money left is "
            "unknown. Check the statement for %s before sending it again."
            % payout.reference))

    tags = _read_response(text)
    txn_status = tags.get("TXNSTATUS", "")
    txnid = tags.get("TXNID", "")
    their_message = tags.get("MESSAGE", "")
    # The envelope carries a PIN, so the request is never logged.
    logger.info("YAS payout %s -> http=%s TXNSTATUS=%s TXNID=%s",
                payout.reference, resp.status_code, txn_status, txnid)

    if txn_status in PAYOUT_OK:
        return finish('paid', txn_status,
                      "TSh %s sent to %s." % (amount, payout.phone_number),
                      txnid)

    if txn_status in PAYOUT_UNKNOWN or not txn_status:
        logger.error("YAS payout %s came back %r. Held.",
                     payout.reference, txn_status or text[:200])
        return finish('held', txn_status, (
            "Mixx by Yas could not confirm this one, so whether the money "
            "left is unknown. Check the statement for %s before sending it "
            "again." % payout.reference), txnid)

    reason = PAYOUT_REASONS.get(txn_status) or their_message or (
        "Mixx by Yas refused it and did not say why.")
    logger.warning("YAS payout %s refused: %s %s",
                   payout.reference, txn_status, reason)
    return finish('failed', txn_status, reason, txnid)


def create_payout(worker, amount, created_by=None, service_request=None,
                  phone_number=""):
    """A payout row, ready to send. Nothing is sent by making one.

    The number is copied onto the row rather than read from the worker's
    profile at send time, so a profile edited between approval and
    sending cannot redirect the money.
    """
    from workers.models import MobileMoneyAccount, WorkerPayout
    from worker_connect.yas import new_payout_reference

    number = str(phone_number or "").strip()
    if not number:
        wallet = (MobileMoneyAccount.objects
                  .filter(user=worker.user, provider='tigo_pesa',
                          is_active=True)
                  .order_by('-is_default', '-created_at').first())
        number = wallet.phone_number if wallet else (
            getattr(worker.user, 'phone_number', '') or "")

    with transaction.atomic():
        return WorkerPayout.objects.create(
            worker=worker,
            service_request=service_request,
            amount=Decimal(str(amount)),
            phone_number=number,
            reference=new_payout_reference(),
            created_by=created_by,
        )


# ---------------------------------------------------------------------------
# Money back: Refund Transaction (spec 1, section 4)
# ---------------------------------------------------------------------------

def configured_for_refunds() -> bool:
    """Is there enough here to send a client their money back?

    The refund call carries the Debit Mandate token, so it needs the
    token URL and the biller login as well as its own route and PIN.
    """
    return bool(can_call_out()
                and _setting("YAS_REFUND_URL")
                and _setting("YAS_TOKEN_URL")
                and _setting("YAS_BILLER_USERNAME")
                and _setting("YAS_BILLER_PASSWORD")
                and _setting("YAS_CHANNEL_MSISDN")
                and _setting("YAS_CHANNEL_PIN"))


def refunds_live() -> bool:
    return _flag("YAS_REFUNDS_ENABLED") and configured_for_refunds()


def create_refund(service_request, amount, phone_number, created_by=None,
                  reason="", mfs_transaction_id="", purchase_reference=""):
    """A refund row, ready to send. Nothing is sent by making one.

    The number is copied onto the row at approval, not read at send
    time, for the same reason as a payout: a profile edited in between
    must not redirect money.
    """
    from clients.models import ClientRefund
    from worker_connect.yas import new_refund_reference

    with transaction.atomic():
        return ClientRefund.objects.create(
            service_request=service_request,
            client=service_request.client,
            amount=Decimal(str(amount)),
            phone_number=str(phone_number or "").strip(),
            reference=new_refund_reference(),
            mfs_transaction_id=str(mfs_transaction_id or "")[:100],
            purchase_reference=str(purchase_reference or "")[:64],
            reason=str(reason or ""),
            created_by=created_by,
        )


def send_refund(refund) -> tuple:
    """Send a client their money back. Returns (state, message).

    Built the same way as send_payout and for the same reasons: the row
    is claimed before the call so a crash cannot leave it looking
    unsent, and anything that is not a clear yes or a clear no lands on
    'held' rather than 'failed'. Money may have moved, and saying it
    certainly did not is the one answer that gets a client paid back
    twice.

    Their specification will only process a refund "if the
    purchase/payment transaction was successful", and needs either the
    original MFSTransactionID or the original payment's reference to
    find it (p.16-17). With neither, nothing is sent.
    """
    from clients.models import ClientRefund

    if not _flag("YAS_REFUNDS_ENABLED"):
        return refund.state, "Refunding by Mixx by Yas is not switched on."
    if not configured_for_refunds():
        logger.warning("YAS refunds are on but not configured.")
        return refund.state, ("Mixx by Yas refunds are switched on but not "
                              "set up yet.")

    number = msisdn(refund.phone_number)
    if not number:
        return refund.state, ("The client's number is not a Tanzanian mobile "
                              "number.")
    amount = whole_shillings(refund.amount)
    if amount <= 0:
        return refund.state, "There is nothing to send back."
    if not (refund.mfs_transaction_id or refund.purchase_reference):
        # Sending without one of these cannot work, and the refusal that
        # comes back is indistinguishable from a dozen others once it
        # arrives. Said here instead, where it is clear.
        return refund.state, (
            "This refund has neither the original transaction id nor the "
            "original reference, so Mixx by Yas cannot find the payment to "
            "reverse.")

    claimed = (ClientRefund.objects
               .filter(pk=refund.pk, state='pending')
               .update(state='sending', sent_at=timezone.now()))
    if not claimed:
        refund.refresh_from_db()
        return refund.state, {
            'sending': "This refund is already on its way.",
            'paid': "This refund has already been sent.",
            'held': ("This refund is held - check the Mixx by Yas statement "
                     "before sending it again."),
            'failed': "This refund failed. Create a new one to try again.",
        }.get(refund.state, "This refund cannot be sent.")
    refund.refresh_from_db()

    def finish(state, code="", message="", their_reference=""):
        refund.state = state
        refund.yas_code = str(code or "")[:40]
        refund.yas_message = str(message or "")
        refund.yas_reference = str(their_reference or "")[:64]
        if state == 'paid':
            refund.settled_at = timezone.now()
        refund.save(update_fields=["state", "yas_code", "yas_message",
                                   "yas_reference", "settled_at"])
        return state, message

    bearer = token()
    if not bearer:
        # No token means the request was never made, so nothing moved.
        # Back to pending, where it can be sent again - unlike a call
        # that went out and was not answered.
        ClientRefund.objects.filter(pk=refund.pk).update(state='pending')
        refund.refresh_from_db()
        return refund.state, ("Mixx by Yas would not issue a token, so "
                              "nothing was sent. Try again shortly.")

    body = {
        "CustomerMSISDN": number,
        "ChannelMSISDN": (msisdn(_setting("YAS_CHANNEL_MSISDN"))
                          or str(_setting("YAS_CHANNEL_MSISDN")).strip()),
        "ChannelPIN": str(_setting("YAS_CHANNEL_PIN")).strip(),
        "Amount": str(amount),
        "ReferenceID": refund.reference,
    }
    # One of these two is mandatory on their side; both are sent when
    # both are known, because which one their gateway actually accepts
    # is the sort of thing only the first real refund settles.
    if refund.mfs_transaction_id:
        body["MFSTransactionID"] = refund.mfs_transaction_id
    if refund.purchase_reference:
        body["PurchaseReferenceID"] = reference_for(refund.purchase_reference)
    headers = {
        "Authorization": "bearer " + bearer,
        "Username": str(_setting("YAS_BILLER_USERNAME")),
        "Password": str(_setting("YAS_BILLER_PASSWORD")),
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    try:
        resp = http_requests.post(str(_setting("YAS_REFUND_URL")), json=body,
                                  headers=headers, timeout=60)
        data = {}
        if resp.content:
            try:
                data = resp.json()
            except ValueError:
                data = {}
        if not isinstance(data, dict):
            data = {}
    except Exception as exc:                                   # noqa: BLE001
        logger.error("YAS refund %s: no answer (%s). Held.",
                     refund.reference, exc)
        return finish('held', "", (
            "Mixx by Yas did not answer, so whether the refund went is "
            "unknown. Check the statement for %s before sending it again."
            % refund.reference))

    # The body carries a PIN and the headers a password, so only the
    # verdict is logged.
    logger.info("YAS refund %s -> http=%s code=%s status=%s",
                refund.reference, resp.status_code, data.get("ResponseCode"),
                data.get("ResponseStatus"))

    code = str(data.get("ResponseCode") or "")
    their_reference = str(data.get("DMReferenceID") or "")
    described = str(data.get("ResponseDescription") or "")
    status_field = data.get("ResponseStatus")
    said_yes = (status_field is True
                or str(status_field).strip().lower() == "true")
    said_no = (status_field is False
               or str(status_field).strip().lower() == "false")

    if said_yes:
        return finish('paid', code,
                      "TSh %s sent back to %s.%s"
                      % (amount, refund.phone_number,
                         " " + described if described else ""),
                      their_reference)
    if said_no:
        return finish('failed', code,
                      described or ("Mixx by Yas refused the refund and did "
                                    "not say why."),
                      their_reference)
    # Neither a yes nor a no. We do not know, so we do not guess.
    logger.error("YAS refund %s gave no clear answer (%r). Held.",
                 refund.reference, status_field)
    return finish('held', code, (
        "Mixx by Yas gave no clear answer, so whether the refund went is "
        "unknown. Check the statement for %s before sending it again."
        % refund.reference), their_reference)
