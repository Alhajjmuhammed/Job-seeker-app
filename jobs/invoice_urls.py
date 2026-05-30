"""
URL routes for invoices.
"""

from django.urls import path
from . import invoice_views

app_name = 'invoices'

urlpatterns = [
    path('', invoice_views.get_my_invoices, name='get_my_invoices'),
    path('create/', invoice_views.create_invoice, name='create_invoice'),
    path('summary/', invoice_views.get_invoice_summary, name='get_invoice_summary'),
    path('<int:invoice_id>/', invoice_views.get_invoice, name='get_invoice'),
    path('<int:invoice_id>/send/', invoice_views.send_invoice, name='send_invoice'),
    path('<int:invoice_id>/paid/', invoice_views.mark_paid, name='mark_paid'),
    path('<int:invoice_id>/cancel/', invoice_views.cancel_invoice, name='cancel_invoice'),
    path('<int:invoice_id>/pdf/', invoice_views.download_invoice_pdf, name='download_invoice_pdf'),
]
