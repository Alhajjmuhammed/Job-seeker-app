"""Mixx by YAS routes.

Mounted at ``api/v1/payments/yas/``, so the two addresses to give YAS
are:

  https://workersearch.co.tz/api/v1/payments/yas/ussd-push/callback/
  https://workersearch.co.tz/api/v1/payments/yas/w2a/

The first is the Biller Callback from the Debit Mandate specification -
it tells us how a prompt we asked for went. The second is SYNC_BILLPAY
from the Partner Integration specification - a client paying from the
Mixx menu, which we are not told about in advance.

Both of those are open routes by necessity: the caller is YAS's gateway
and cannot log in. What stands in for a login is in yas.py - a shared
secret, the biller username and password, or their gateway's address -
and with none of the three configured every call is refused.

Everything else here needs a login, and the payout routes need staff.
"""
from django.urls import path

from worker_connect import yas, yas_views

app_name = 'yas'

urlpatterns = [
    # --- YAS call us (no login possible; see yas.secret_ok) --------------
    path('ussd-push/callback/',
         yas.YasUssdPushCallbackView.as_view(),
         name='ussd-push-callback'),
    path('w2a/',
         yas.YasBillPaymentView.as_view(),
         name='w2a'),

    # --- a client pays for their own booking -----------------------------
    path('pay/<int:request_id>/',
         yas_views.pay_service_request, name='pay'),
    path('instructions/<int:request_id>/',
         yas_views.payment_instructions, name='instructions'),

    # --- an admin pays a worker ------------------------------------------
    path('payouts/', yas_views.payouts, name='payouts'),
    path('payouts/<int:payout_id>/send/',
         yas_views.send_payout, name='payout-send'),
    path('payouts/<int:payout_id>/resolve/',
         yas_views.resolve_payout, name='payout-resolve'),

    # --- an admin sends a client their money back ------------------------
    path('refunds/', yas_views.refunds, name='refunds'),
    path('refunds/<int:refund_id>/send/',
         yas_views.send_refund, name='refund-send'),
    path('refunds/<int:refund_id>/resolve/',
         yas_views.resolve_refund, name='refund-resolve'),
    path('payments/<int:payment_id>/confirm-amount/',
         yas_views.confirm_payment_amount, name='payment-confirm-amount'),

    # --- what the admin screen reads -------------------------------------
    path('status/', yas_views.yas_status, name='status'),
]
