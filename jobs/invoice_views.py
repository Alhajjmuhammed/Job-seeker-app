"""
Invoice API views for Worker Connect.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse

from .invoices import Invoice, InvoiceItem, InvoiceService
from workers.models import WorkerProfile
from clients.models import ClientProfile
from jobs.models import JobRequest


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_invoices(request):
    """
    Get invoices for the current user (worker or client).
    """
    status_filter = request.query_params.get('status')
    
    # Check if user is worker or client
    try:
        worker = WorkerProfile.objects.get(user=request.user)
        invoices = InvoiceService.get_worker_invoices(worker, status_filter)
        role = 'worker'
    except WorkerProfile.DoesNotExist:
        try:
            client = ClientProfile.objects.get(user=request.user)
            invoices = InvoiceService.get_client_invoices(client, status_filter)
            role = 'client'
        except ClientProfile.DoesNotExist:
            return Response({
                'error': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    invoice_data = []
    for inv in invoices:
        invoice_data.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'description': inv.description,
            'status': inv.status,
            'subtotal': str(inv.subtotal),
            'tax_amount': str(inv.tax_amount),
            'discount': str(inv.discount),
            'total': str(inv.total),
            'issue_date': inv.issue_date.isoformat(),
            'due_date': inv.due_date.isoformat(),
            'paid_date': inv.paid_date.isoformat() if inv.paid_date else None,
            'job_id': inv.job_id,
            'worker_id': inv.worker_id,
            'client_id': inv.client_id,
        })
    
    return Response({
        'role': role,
        'invoices': invoice_data,
        'count': len(invoice_data),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invoice(request, invoice_id):
    """
    Get a specific invoice with line items.
    """
    invoice = InvoiceService.get_invoice(invoice_id, request.user)
    
    if not invoice:
        return Response({
            'error': 'Invoice not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    
    items = []
    for item in invoice.items.all():
        items.append({
            'id': item.id,
            'description': item.description,
            'quantity': str(item.quantity),
            'unit_price': str(item.unit_price),
            'total': str(item.total),
        })
    
    return Response({
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'description': invoice.description,
        'status': invoice.status,
        'subtotal': str(invoice.subtotal),
        'tax_rate': str(invoice.tax_rate),
        'tax_amount': str(invoice.tax_amount),
        'discount': str(invoice.discount),
        'total': str(invoice.total),
        'issue_date': invoice.issue_date.isoformat(),
        'due_date': invoice.due_date.isoformat(),
        'paid_date': invoice.paid_date.isoformat() if invoice.paid_date else None,
        'notes': invoice.notes,
        'terms': invoice.terms,
        'items': items,
        'job_id': invoice.job_id,
        'worker': {
            'id': invoice.worker_id,
            'name': invoice.worker.user.get_full_name() if invoice.worker else '',
        },
        'client': {
            'id': invoice.client_id,
            'name': invoice.client.user.get_full_name() if invoice.client else '',
        },
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_invoice(request):
    """
    Create a new invoice (workers only).
    
    Request body:
        {
            "job_id": 1,
            "client_id": 1,
            "items": [
                {"description": "Labor - 4 hours", "quantity": 4, "unit_price": 50},
                {"description": "Materials", "quantity": 1, "unit_price": 100}
            ],
            "tax_rate": 10,
            "discount": 0,
            "notes": "Thank you for your business",
            "terms": "Payment due within 14 days",
            "due_days": 14
        }
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can create invoices'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get client
    client_id = request.data.get('client_id')
    if not client_id:
        return Response({
            'error': 'client_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        client = ClientProfile.objects.get(id=client_id)
    except ClientProfile.DoesNotExist:
        return Response({
            'error': 'Client not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get job (optional but recommended)
    job = None
    job_id = request.data.get('job_id')
    if job_id:
        try:
            job = JobRequest.objects.get(id=job_id)
        except JobRequest.DoesNotExist:
            return Response({
                'error': 'Job not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    # Get items
    items = request.data.get('items', [])
    if not items:
        return Response({
            'error': 'At least one item is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate items
    for item in items:
        if not all(k in item for k in ['description', 'quantity', 'unit_price']):
            return Response({
                'error': 'Each item must have description, quantity, and unit_price'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    invoice = InvoiceService.create_invoice(
        worker=worker,
        client=client,
        job=job,
        items=items,
        tax_rate=request.data.get('tax_rate', 0),
        discount=request.data.get('discount', 0),
        notes=request.data.get('notes', ''),
        terms=request.data.get('terms', ''),
        due_days=request.data.get('due_days', 30),
    )
    
    return Response({
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'total': str(invoice.total),
        'message': 'Invoice created successfully'
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_invoice(request, invoice_id):
    """
    Mark invoice as sent.
    """
    invoice = InvoiceService.get_invoice(invoice_id, request.user)
    
    if not invoice:
        return Response({
            'error': 'Invoice not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Only workers can send invoices
    try:
        worker = WorkerProfile.objects.get(user=request.user)
        if invoice.worker != worker:
            return Response({
                'error': 'Only the invoice creator can send it'
            }, status=status.HTTP_403_FORBIDDEN)
    except WorkerProfile.DoesNotExist:
        return Response({
            'error': 'Only workers can send invoices'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if invoice.status != 'draft':
        return Response({
            'error': 'Only draft invoices can be sent'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    InvoiceService.mark_as_sent(invoice)
    
    return Response({
        'id': invoice.id,
        'status': invoice.status,
        'message': 'Invoice sent successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_paid(request, invoice_id):
    """
    Mark invoice as paid.
    """
    invoice = InvoiceService.get_invoice(invoice_id, request.user)
    
    if not invoice:
        return Response({
            'error': 'Invoice not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if invoice.status not in ['sent', 'overdue']:
        return Response({
            'error': 'Only sent or overdue invoices can be marked as paid'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    InvoiceService.mark_as_paid(invoice)
    
    return Response({
        'id': invoice.id,
        'status': invoice.status,
        'paid_date': invoice.paid_date.isoformat(),
        'message': 'Invoice marked as paid'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_invoice(request, invoice_id):
    """
    Cancel an invoice.
    """
    invoice = InvoiceService.get_invoice(invoice_id, request.user)
    
    if not invoice:
        return Response({
            'error': 'Invoice not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if invoice.status == 'paid':
        return Response({
            'error': 'Cannot cancel a paid invoice'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    InvoiceService.cancel_invoice(invoice)
    
    return Response({
        'id': invoice.id,
        'status': invoice.status,
        'message': 'Invoice cancelled'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice_pdf(request, invoice_id):
    """
    Download invoice as PDF.
    """
    invoice = InvoiceService.get_invoice(invoice_id, request.user)
    
    if not invoice:
        return Response({
            'error': 'Invoice not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    
    pdf = InvoiceService.generate_pdf(invoice)
    
    if not pdf:
        return Response({
            'error': 'PDF generation not available'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invoice_summary(request):
    """
    Get invoice summary statistics.
    """
    try:
        worker = WorkerProfile.objects.get(user=request.user)
        summary = InvoiceService.get_invoice_summary(worker=worker)
        role = 'worker'
    except WorkerProfile.DoesNotExist:
        try:
            client = ClientProfile.objects.get(user=request.user)
            summary = InvoiceService.get_invoice_summary(client=client)
            role = 'client'
        except ClientProfile.DoesNotExist:
            return Response({
                'error': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'role': role,
        'summary': {
            'total_invoices': summary['total_invoices'],
            'by_status': {
                'draft': summary['draft'],
                'sent': summary['sent'],
                'paid': summary['paid'],
                'overdue': summary['overdue'],
                'cancelled': summary['cancelled'],
            },
            'amounts': {
                'total': str(summary['total_amount']),
                'paid': str(summary['paid_amount']),
                'outstanding': str(summary['outstanding_amount']),
            }
        }
    })
