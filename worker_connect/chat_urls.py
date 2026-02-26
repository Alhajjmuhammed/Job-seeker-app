from django.urls import path
from . import chat_views

app_name = 'wc_chat'

urlpatterns = [
    path('conversations/', chat_views.conversation_list, name='conversation_list'),
    path('conversations/<int:conversation_id>/messages/', chat_views.conversation_messages, name='conversation_messages'),
    path('conversations/<int:conversation_id>/read/', chat_views.mark_as_read, name='mark_as_read'),
    path('conversations/start/', chat_views.start_conversation, name='start_conversation'),
    path('conversations/search/', chat_views.search_conversations, name='search_conversations'),
    path('messages/send/', chat_views.send_message, name='send_message'),
    path('messages/<int:message_id>/delete/', chat_views.delete_message, name='delete_message'),
    path('unread-count/', chat_views.unread_count, name='unread_count'),
]