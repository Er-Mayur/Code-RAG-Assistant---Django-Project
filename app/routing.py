"""
WebSocket routing for real-time chat
"""
from django.urls import path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/chat/<int:session_id>/', ChatConsumer.as_asgi()),
]
