from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .support_models import SupportTicket, SupportMessage, FAQ
from .support_serializers import (
    SupportTicketCreateSerializer,
    SupportTicketSerializer,
    SupportMessageSerializer,
    FAQSerializer
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_support_ticket(request):
    """Create a new support ticket"""
    serializer = SupportTicketCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        ticket = serializer.save()
        return Response({
            'success': True,
            'message': 'Support ticket created successfully',
            'ticket_id': ticket.id
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_support_tickets(request):
    """Get user's support tickets"""
    tickets = SupportTicket.objects.filter(user=request.user)
    serializer = SupportTicketSerializer(tickets, many=True)
    
    return Response({
        'success': True,
        'tickets': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def support_ticket_detail(request, ticket_id):
    """Get support ticket details"""
    ticket = get_object_or_404(SupportTicket, id=ticket_id, user=request.user)
    serializer = SupportTicketSerializer(ticket)
    
    return Response({
        'success': True,
        'ticket': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_ticket_message(request, ticket_id):
    """Add a message to support ticket"""
    ticket = get_object_or_404(SupportTicket, id=ticket_id, user=request.user)
    
    message_text = request.data.get('message', '').strip()
    if not message_text:
        return Response({
            'success': False,
            'error': 'Message content is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    message = SupportMessage.objects.create(
        ticket=ticket,
        sender=request.user,
        message=message_text
    )
    
    # Update ticket status to indicate user response
    if ticket.status == 'resolved':
        ticket.status = 'open'
        ticket.save()
    
    serializer = SupportMessageSerializer(message)
    return Response({
        'success': True,
        'message': serializer.data
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([AllowAny])
def faq_list(request):
    """Get FAQ list"""
    category = request.GET.get('category', None)
    faqs = FAQ.objects.filter(is_active=True)
    
    if category:
        faqs = faqs.filter(category=category)
    
    serializer = FAQSerializer(faqs, many=True)
    
    # Group by category
    faq_by_category = {}
    for faq in serializer.data:
        cat = faq['category']
        if cat not in faq_by_category:
            faq_by_category[cat] = []
        faq_by_category[cat].append(faq)
    
    return Response({
        'success': True,
        'faqs_by_category': faq_by_category,
        'categories': [
            {'value': 'general', 'label': 'General'},
            {'value': 'worker', 'label': 'For Workers'},
            {'value': 'client', 'label': 'For Clients'},
            {'value': 'payment', 'label': 'Payments'},
            {'value': 'technical', 'label': 'Technical'},
        ]
    })