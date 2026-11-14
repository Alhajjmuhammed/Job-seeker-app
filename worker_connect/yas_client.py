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


# gunicorn kills a worker after 30 seconds (gunicorn_config.py). A money
# call still waiting when that happens leaves its row in 'sending' with
# nobody left to finish it, so no single call may wait longer than this,
# whatever the settings say - and the token and the money call together
# stay below gunicorn's limit with the defaults (8 + 20).
_MOST_ANY_CALL_MAY_WAIT = 25


def _timeout(name, default) -> float:
    try:
        value = float(_setting(name, default))
    except (TypeError, ValueError):
        value = float(default)
    if not value > 0:
        value = float(default)
    return min(value, _MOST_ANY_CALL_MAY_WAIT)


def http_timeout() -> float:
    """Seconds to wait on a payment, payout or refund call."""
    return _timeout("YAS_HTTP_TIMEOUT", 20)


def token_timeout() -> float:
    """Seconds to wait for a token."""
    return _timeout("YAS_TOKEN_TIMEOUT", 8)


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

    # Seconds plus eight random digits, still 22 digits in all. The
    # microseconds this used to carry are not real on every platform -
    # on Windows the clock moves in steps of a millisecond or more, so
    # fifty fast attempts collided on two random digits. Eight random
    # digits make a repeat within one second about one in two million
    # for fifty attempts.
    return (_tz.now().strftime("%Y%m%d%H%M%S")
            + "".join(secrets.choice("0123456789") for _ in range(8)))


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
            timeout=token_timeout(),
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


def request_payment(phone, amount_tzs, request_ref, remarks="",
                    reference_id=None, report=None) -> tuple:
    """Ask a client's phone for the money. Returns (sent, message).

    reference_id is the exact ReferenceID to send (the caller stores it
    first, so the callback and any refund can name this very attempt);
    without one a fresh attempt marker is made here. When ``report`` is a
    dict, ``report["maybe_sent"]`` is set True if the request went out
    and no answer came back - the prompt may be ringing even though this
    returns False.

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
        "ReferenceID": (str(reference_id) if reference_id
                        else reference_for(request_ref,
                                           new_attempt_marker())),
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
        if isinstance(report, dict):
            report["maybe_sent"] = True
        resp = http_requests.post(url, json=body, headers=headers,
                                  timeout=http_timeout())
        if isinstance(report, dict):
            report["maybe_sent"] = False
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


def send_payout(payout, sent_by=None) -> tuple:
    """Send a worker their money. Returns (state, message).

    Whether ``sent_by`` may send it (four-eyes, permissions) is decided
    by the caller - yas_views.send_payout - before this is reached.

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
    claim = {"state": 'sending', "sent_at": timezone.now()}
    if sent_by is not None:
        claim["sent_by"] = sent_by
    with transaction.atomic():
        row = (WorkerPayout.objects.select_for_update()
               .filter(pk=payout.pk).first())
        if row is not None and row.state == 'pending':
            problem = payout_problem(row.worker, row.service_request,
                                     row.amount, exclude_pk=row.pk)
            if problem:
                logger.warning("YAS payout %s not sent: %s",
                               payout.reference, problem)
                return row.state, problem + " Nothing was sent."
        claimed = (WorkerPayout.objects
                   .filter(pk=payout.pk, state='pending')
                   .update(**claim))
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
                                  headers=headers, timeout=http_timeout())
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


class PayoutRefused(ValueError):
    """A payout that may not be made. The message is for the admin."""


class RefundRefused(ValueError):
    """A refund that may not be made. The message is for the admin."""


def second_approver_required() -> bool:
    return bool(_setting("YAS_REQUIRE_SECOND_APPROVER", True))


def registered_number(worker) -> str:
    """The worker's own number: their Tigo/Mixx wallet, else their account's."""
    from workers.models import MobileMoneyAccount

    # Verified wallets only, and nothing else. An unverified wallet - or
    # the account's own phone, which the worker edits freely - is just a
    # number somebody typed. With no verified wallet there is no default
    # destination: the admin has to name one, with a reason, and a second
    # person sends it.
    wallet = (MobileMoneyAccount.objects
              .filter(user=worker.user, provider='tigo_pesa', is_active=True,
                      is_verified=True)
              .order_by('-is_default', '-created_at').first())
    return wallet.phone_number.strip() if wallet else ""


def payout_problem(worker, service_request, value, exclude_pk=None):
    """Why this payout may not be made (or sent) now, or "" when it may.

    Checked when it is approved and again, with the rows locked, just
    before it is sent - so a payout approved under older, looser rules,
    or whose booking was refunded in between, cannot leave.
    """
    from jobs.service_request_models import (ServiceRequest,
                                             ServiceRequestAssignment)
    from workers.models import WorkerPayout

    if service_request is None:
        return "This payout names no booking."
    booking = (ServiceRequest.objects.select_for_update()
               .filter(pk=service_request.pk).first())
    if booking is None:
        return "The booking this payout is for no longer exists."
    if booking.payment_status == 'refunded':
        return "The client was refunded for this booking."
    if not booking.is_paid:
        return "The client has not paid for this booking."
    assignment = (ServiceRequestAssignment.objects.select_for_update()
                  .filter(service_request=booking, worker=worker,
                          status='completed').first())
    if assignment is None:
        return ("This worker has no completed assignment on that booking, "
                "so there is nothing to pay.")
    others = (WorkerPayout.objects
              .filter(worker=worker, service_request=booking)
              .exclude(state='failed'))
    if exclude_pk is not None:
        others = others.exclude(pk=exclude_pk)
    earned = Decimal(str(assignment.worker_payment or 0))
    spent = sum((p.amount for p in others), Decimal("0"))
    if Decimal(str(value)) > earned - spent:
        return ("That is more than this worker earned on this booking "
                "(TSh %s)." % (earned - spent))
    return ""


def create_payout(worker, amount, created_by=None, service_request=None,
                  phone_number="", override_reason=""):
    """A payout row, ready to send. Nothing is sent by making one.

    A payout pays a worker for one job, and only what they earned on it:

      the worker must have a COMPLETED assignment on ``service_request``;
      the amount may not exceed that assignment's worker_payment;
      one live (not failed) payout per worker per job - a database
      constraint, and checked here with the assignment row locked.

    The destination is the worker's own registered number. Another number
    is only accepted with an ``override_reason``, is recorded on the row
    with who set it, and is refused outright when
    YAS_REQUIRE_SECOND_APPROVER is off - with nobody else checking, one
    person could otherwise send a worker's pay to their own phone.

    The number is copied onto the row rather than read from the worker's
    profile at send time, so a profile edited between approval and
    sending cannot redirect the money.

    Raises PayoutRefused with a message for the admin.
    """
    from django.db import IntegrityError
    from workers.models import WorkerPayout
    from worker_connect.yas import new_payout_reference

    if service_request is None:
        raise PayoutRefused("A payout must name the booking it pays for "
                            "(service_request_id).")
    try:
        value = Decimal(str(amount))
        if not value.is_finite() or value <= 0:
            raise ValueError
    except Exception:                                         # noqa: BLE001
        raise PayoutRefused("amount must be more than zero.")
    if whole_shillings(value) <= 0:
        raise PayoutRefused("amount must be at least one shilling.")

    registered = registered_number(worker)
    asked = str(phone_number or "").strip()
    note = ""
    if not registered and not asked:
        raise PayoutRefused(
            "This worker has no verified Mixx by Yas wallet. Verify one, or "
            "name the number to pay (phone_number) and say why "
            "(override_reason).")
    if asked and msisdn(asked) != msisdn(registered):
        if not second_approver_required():
            raise PayoutRefused(
                "A payout can only go to the worker's own registered number "
                "while YAS_REQUIRE_SECOND_APPROVER is off.")
        reason = str(override_reason or "").strip()
        if not reason:
            raise PayoutRefused(
                "That is not the worker's registered number. Say why it "
                "should go there instead (override_reason).")
        who = (created_by.get_full_name() or created_by.username
               if created_by is not None else "unknown")
        note = ("Destination set by %s instead of the registered number "
                "%s: %s" % (who, registered or "(none)", reason))
        number = asked
    else:
        number = registered

    with transaction.atomic():
        live = list(WorkerPayout.objects.select_for_update()
                    .filter(worker=worker, service_request=service_request)
                    .exclude(state='failed'))
        if live:
            raise PayoutRefused(
                "This worker already has a payout for this booking (%s, %s)."
                % (live[0].reference, live[0].get_state_display()))
        problem = payout_problem(worker, service_request, value)
        if problem:
            raise PayoutRefused(problem)
        try:
            with transaction.atomic():
                return WorkerPayout.objects.create(
                    worker=worker,
                    service_request=service_request,
                    amount=value,
                    phone_number=number,
                    reference=new_payout_reference(),
                    created_by=created_by,
                    destination_note=note,
                )
        except IntegrityError:
            raise PayoutRefused("This worker already has a payout for this "
                                "booking.")


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


def gateway_payments(service_request, refundable_only=False):
    """Real Mixx by Yas money recorded against this booking.

    refundable_only leaves out rows whose amount nobody has confirmed: YAS
    said money was taken without saying how much, so the figure on the row
    is only what we asked for and cannot be a refund cap.
    """
    from django.db.models import Q
    from clients.models import PaymentTransaction

    rows = (PaymentTransaction.objects
            .filter(method='yas', is_demo=False)
            .filter(Q(service_request=service_request)
                    | Q(consumed_by=service_request)))
    if refundable_only:
        rows = rows.filter(amount_confirmed=True)
    return rows


def _refunded_against(rows) -> int:
    """Whole shillings already sent back, or on their way, for these rows."""
    return sum(whole_shillings(r.amount) for r in rows)


def refund_problem(refund):
    """Why this refund may not be sent now, or "" when it may.

    Checked again, with the payment locked, just before sending - so a
    refund approved under older, looser rules cannot leave: it must
    reverse a real, confirmed Mixx by Yas payment and stay within what
    that payment brought in.
    """
    from clients.models import ClientRefund, PaymentTransaction

    if refund.payment_id is None:
        return "This refund is not linked to a recorded Mixx by Yas payment."
    payment = (PaymentTransaction.objects.select_for_update()
               .filter(pk=refund.payment_id, method='yas', is_demo=False)
               .first())
    if payment is None:
        return "The payment this refund reverses is not a Mixx by Yas payment."
    if not payment.amount_confirmed:
        return ("The amount of the payment this reverses has not been "
                "confirmed from the statement yet.")
    others = (ClientRefund.objects.filter(payment=payment)
              .exclude(state='failed').exclude(pk=refund.pk))
    if (whole_shillings(refund.amount) + _refunded_against(others)
            > whole_shillings(payment.amount)):
        return "That is more than is left to refund on this payment."
    return ""


def confirm_payment_amount(payment_id, amount, note, user):
    """A person confirms, from the statement, what an unconfirmed payment was.

    Until then the row is not refundable. Four-eyes: whoever confirms the
    amount may not also approve the refund of it (create_refund checks).
    Raises RefundRefused.
    """
    from clients.models import PaymentTransaction
    from worker_connect.yas import MOST_THEY_CAN_SEND

    note = str(note or "").strip()
    if len(note) < 5:
        raise RefundRefused("Say what you checked (note) - the statement "
                            "line that shows the amount.")
    try:
        value = Decimal(str(amount))
        if not value.is_finite() or value <= 0 or value > MOST_THEY_CAN_SEND:
            raise ValueError
    except Exception:                                         # noqa: BLE001
        raise RefundRefused("amount must be more than zero.")
    who = (user.get_full_name() or user.username) if user else "unknown"
    with transaction.atomic():
        row = (PaymentTransaction.objects.select_for_update()
               .filter(pk=payment_id, method='yas', is_demo=False).first())
        if row is None:
            raise RefundRefused("No Mixx by Yas payment with that id.")
        if row.amount_confirmed:
            raise RefundRefused("This payment's amount is already confirmed.")
        # A push charges exactly what we asked for, which is what the row
        # holds. The statement can show less (or the same), never more -
        # a bigger figure here would only inflate the refund cap.
        asked_for = whole_shillings(row.amount)
        if whole_shillings(value) <= 0:
            raise RefundRefused("amount must be at least one shilling.")
        if value > asked_for:
            raise RefundRefused(
                "That is more than we asked the client for (TSh %s). A "
                "prompt cannot take more than it asked." % asked_for)
        was = row.amount
        row.amount = value
        row.amount_confirmed = True
        row.amount_confirmed_by = user
        row.amount_note = ("Amount confirmed by %s as TSh %s (recorded as "
                           "%s): %s" % (who, value, was, note))
        row.save(update_fields=["amount", "amount_confirmed",
                                "amount_confirmed_by", "amount_note"])
    logger.info("YAS payment #%s amount confirmed as %s by %s",
                row.pk, value, who)
    return row


def create_refund(service_request, amount=None, phone_number="",
                  created_by=None, reason="", mfs_transaction_id="",
                  purchase_reference="", payment=None, override_reason=""):
    """A refund row, ready to send. Nothing is sent by making one.

    A refund reverses one recorded Mixx by Yas payment and is capped at
    what that payment brought in:

      the booking must have real (non-demo) YAS money recorded against
      it, with a confirmed amount - ``payment``, or its one applied
      payment when none is named;
      amount > 0, and every refund that has not failed against that
      payment, this one included, adds up to no more than it brought in;
      the booking and the payment are locked while that is checked;
      whoever confirmed an unreported amount may not approve its refund.

    The money goes back to the wallet it came from (the payment's
    payer_msisdn). When that is unknown it goes to the client's profile
    number, and the row says so in destination_note. Any other number
    needs an ``override_reason``, is recorded with who set it, and is
    refused while YAS_REQUIRE_SECOND_APPROVER is off.

    The receipt and ReferenceID sent to YAS are the ones recorded at pay
    time, copied from the payment - never re-derived, and never typed in.
    mfs_transaction_id / purchase_reference are accepted only when they
    agree with the payment.

    Raises RefundRefused with a message for the admin.
    """
    from clients.models import ClientRefund, PaymentTransaction
    from jobs.service_request_models import ServiceRequest
    from worker_connect.yas import new_refund_reference

    with transaction.atomic():
        booking = (ServiceRequest.objects.select_for_update()
                   .get(pk=service_request.pk))
        candidates = gateway_payments(booking)
        if payment is not None:
            chosen = (candidates.select_for_update()
                      .filter(pk=getattr(payment, 'pk', payment)).first())
            if chosen is None:
                raise RefundRefused("That payment is not a Mixx by Yas "
                                    "payment for this booking.")
        else:
            applied = list(candidates.filter(unapplied_reason=''))
            pool = applied or list(candidates)
            if not pool:
                raise RefundRefused(
                    "This booking has no Mixx by Yas payment recorded, so "
                    "there is nothing to refund through Mixx by Yas.")
            if len(pool) > 1:
                raise RefundRefused(
                    "This booking has more than one Mixx by Yas payment. "
                    "Name the one to refund (payment_id).")
            chosen = (PaymentTransaction.objects.select_for_update()
                      .get(pk=pool[0].pk))

        if not chosen.amount_confirmed:
            raise RefundRefused(
                "YAS did not report how much this payment was. Confirm the "
                "amount from the statement first (confirm-amount).")
        if (second_approver_required() and created_by is not None
                and chosen.amount_confirmed_by_id == created_by.pk):
            raise RefundRefused("You confirmed this payment's amount, so "
                                "somebody else has to approve its refund.")

        receipt = chosen.reference
        if receipt.startswith("NORCPT-"):
            receipt = ""
        if mfs_transaction_id and str(mfs_transaction_id) != receipt:
            raise RefundRefused("mfs_transaction_id does not match the "
                                "recorded payment.")
        if (purchase_reference
                and str(purchase_reference) != chosen.gateway_reference):
            raise RefundRefused("purchase_reference does not match the "
                                "recorded payment.")

        brought_in = whole_shillings(chosen.amount)
        already = _refunded_against(
            ClientRefund.objects.select_for_update()
            .filter(payment=chosen).exclude(state='failed'))
        left = brought_in - already
        if left <= 0:
            raise RefundRefused("This payment has already been refunded in "
                                "full.")
        try:
            value = (Decimal(left).quantize(Decimal("0.01"))
                     if amount in (None, "") else Decimal(str(amount)))
            if not value.is_finite() or value <= 0:
                raise ValueError
        except Exception:                                     # noqa: BLE001
            raise RefundRefused("amount must be more than zero.")
        if whole_shillings(value) <= 0:
            raise RefundRefused("amount must be at least one shilling.")
        if whole_shillings(value) > left:
            raise RefundRefused(
                "That is more than is left to refund on this payment "
                "(TSh %s of TSh %s)." % (max(left, 0), brought_in))

        # And across the booking as a whole, in case older refunds were
        # made before refunds named their payment.
        total_in = _refunded_against(
            gateway_payments(booking, refundable_only=True))
        total_out = _refunded_against(
            ClientRefund.objects.filter(service_request=booking)
            .exclude(state='failed'))
        if total_out + whole_shillings(value) > total_in:
            raise RefundRefused("That is more than this booking brought in "
                                "through Mixx by Yas.")

        # Where it goes: back to the wallet it came from.
        payer = msisdn(chosen.payer_msisdn)
        if payer:
            default, note = payer, ""
        else:
            default = (getattr(booking.client, 'phone_number', '')
                       or "").strip()
            note = ("The payer's number was not reported, so this goes to "
                    "the client's profile number.")
        asked = str(phone_number or "").strip()
        if asked and msisdn(asked) != msisdn(default):
            if not second_approver_required():
                raise RefundRefused(
                    "A refund can only go back to the paying wallet while "
                    "YAS_REQUIRE_SECOND_APPROVER is off.")
            why = str(override_reason or "").strip()
            if not why:
                raise RefundRefused(
                    "That is not the number the payment came from. Say why "
                    "it should go there instead (override_reason).")
            who = ((created_by.get_full_name() or created_by.username)
                   if created_by is not None else "unknown")
            note = ("%sDestination set by %s instead of %s: %s"
                    % (note + " " if note else "", who,
                       default or "(none)", why))
            number = asked
        else:
            number = default

        return ClientRefund.objects.create(
            service_request=booking,
            client=booking.client,
            amount=value,
            phone_number=number,
            reference=new_refund_reference(),
            mfs_transaction_id=receipt[:100],
            purchase_reference=chosen.gateway_reference[:64],
            reason=str(reason or ""),
            created_by=created_by,
            payment=chosen,
            destination_note=note,
        )


def after_refund_paid(refund) -> None:
    """A refund went through. Mark the booking refunded when it is complete.

    Only for the payment that paid the booking: once everything it
    brought in has gone back, the booking reads 'refunded' and can take no
    more money. A partial refund leaves it as it is - the refund rows are
    the record of what went back - and says so in the log. Money that was
    never applied (unapplied_reason) does not change the booking at all.
    """
    from clients.models import ClientRefund
    from jobs.service_request_models import ServiceRequest

    payment = refund.payment
    if payment is None or refund.service_request_id is None:
        return
    sent_back = _refunded_against(
        ClientRefund.objects.filter(payment=payment, state='paid'))
    whole = sent_back >= whole_shillings(payment.amount)
    if payment.unapplied_reason:
        logger.info("Refund %s returned TSh %s of unapplied payment %s.",
                    refund.reference, sent_back, payment.reference)
        return
    if whole:
        ServiceRequest.objects.filter(pk=refund.service_request_id).update(
            payment_status='refunded')
        logger.info("Refund %s completes the refund of %s; booking marked "
                    "refunded.", refund.reference, payment.reference)
    else:
        logger.info("Refund %s is partial: TSh %s of %s returned for %s.",
                    refund.reference, sent_back,
                    whole_shillings(payment.amount), payment.reference)


def send_refund(refund, sent_by=None) -> tuple:
    """Send a client their money back. Returns (state, message).

    Whether ``sent_by`` may send it (four-eyes, permissions) is decided
    by the caller - yas_views.send_refund - before this is reached.

    The token is fetched before the row is claimed: a worker killed while
    waiting for a token used to leave the row in 'sending' although
    nothing had gone out.

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

    def not_sendable():
        refund.refresh_from_db()
        return refund.state, {
            'sending': "This refund is already on its way.",
            'paid': "This refund has already been sent.",
            'held': ("This refund is held - check the Mixx by Yas statement "
                     "before sending it again."),
            'failed': "This refund failed. Create a new one to try again.",
        }.get(refund.state, "This refund cannot be sent.")

    if not ClientRefund.objects.filter(pk=refund.pk,
                                       state='pending').exists():
        return not_sendable()

    bearer = token()
    if not bearer:
        # No token means the request was never made, so nothing moved,
        # and the row was never claimed: it is still pending and can be
        # sent again - unlike a call that went out and was not answered.
        refund.refresh_from_db()
        return refund.state, ("Mixx by Yas would not issue a token, so "
                              "nothing was sent. Try again shortly.")

    claim = {"state": 'sending', "sent_at": timezone.now()}
    if sent_by is not None:
        claim["sent_by"] = sent_by
    with transaction.atomic():
        row = (ClientRefund.objects.select_for_update()
               .filter(pk=refund.pk).first())
        if row is not None and row.state == 'pending':
            problem = refund_problem(row)
            if problem:
                logger.warning("YAS refund %s not sent: %s",
                               refund.reference, problem)
                return row.state, problem + " Nothing was sent."
        claimed = (ClientRefund.objects
                   .filter(pk=refund.pk, state='pending')
                   .update(**claim))
    if not claimed:
        return not_sendable()
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
        if state == 'paid':
            after_refund_paid(refund)
        return state, message

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
        # Exactly the ReferenceID the original payment was made with, as
        # recorded at pay time - biller code and attempt marker included.
        # Re-deriving it from the booking reference dropped the marker,
        # and YAS could not find the payment to reverse.
        body["PurchaseReferenceID"] = refund.purchase_reference
    headers = {
        "Authorization": "bearer " + bearer,
        "Username": str(_setting("YAS_BILLER_USERNAME")),
        "Password": str(_setting("YAS_BILLER_PASSWORD")),
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    try:
        resp = http_requests.post(str(_setting("YAS_REFUND_URL")), json=body,
                                  headers=headers, timeout=http_timeout())
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
