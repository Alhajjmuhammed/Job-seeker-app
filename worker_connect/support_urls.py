from django.urls import path
from . import support_views

app_name = 'wc_support'

urlpatterns = [
    # Root support API endpoint - use FAQ as default
    path('', support_views.faq_list, name='support_root'),
    
    path('ticket/', support_views.create_support_ticket, name='create_ticket'),
    path('tickets/', support_views.my_support_tickets, name='my_tickets'),
    path('ticket/<int:ticket_id>/', support_views.support_ticket_detail, name='ticket_detail'),
    path('ticket/<int:ticket_id>/message/', support_views.add_ticket_message, name='add_message'),
    path('faq/', support_views.faq_list, name='faq_list'),
]