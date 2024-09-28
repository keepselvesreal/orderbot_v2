"""
ASGI config for orderbot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter 
import django
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orderbot.settings.development')
django.setup()

from chat.consumers import ChatConsumer
from chat.middleware import JWTAuthMiddleware


django_asgi_app = get_asgi_application()

websocket_urlpatterns = [
    re_path(r'ws/chat/room/(?P<user_id>\d+)/$', ChatConsumer.as_asgi()),
]

print("asgi.py 진입")
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})