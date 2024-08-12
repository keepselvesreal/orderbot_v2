"""
ASGI config for orderbot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack 
import django
from django.urls import re_path
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orderbot.settings')
django.setup()

import chat.routing
from chat.consumers import ChatConsumer

django_asgi_app = get_asgi_application()
# django_asgi_app = WhiteNoise(django_asgi_app, root='/staticfiles')

websocket_urlpatterns = [
    re_path(r'ws/chat/room/(?P<user_id>\d+)/$', ChatConsumer.as_asgi()),
]

print("asgi.py 진입")
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})