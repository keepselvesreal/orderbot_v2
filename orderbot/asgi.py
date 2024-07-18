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

# ts 프런트엔드 장고 템플릿 사용 시
# application = ProtocolTypeRouter({
#     "http": django_asgi_app,
#     "websocket": AuthMiddlewareStack(
#         URLRouter(chat.routing.websocket_urlpatterns)
#     ),
# })

from chat.middleware import TokenAuthMiddleware

# ts. 프런트엔드 리액트 사용 시
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})