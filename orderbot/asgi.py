"""
ASGI config for orderbot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter # ts
from channels.auth import AuthMiddlewareStack # ts
import chat.routing # ts

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orderbot.settings")

# application = get_asgi_application()
django_asgi_app = get_asgi_application() # ts

# ts
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(chat.routing.websocket_urlpatterns)
    ),
})

