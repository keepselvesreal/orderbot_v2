# middleware.py
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware

User = get_user_model()

@database_sync_to_async
def get_user(token):
    try:
        access_token = AccessToken(token)
        user = User.objects.get(id=access_token['user_id'])
        return user
    except Exception:
        return AnonymousUser()

class JWTAuthMiddleware:
    """
    Custom middleware to authenticate JWT in the WebSocket connection.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # WebSocket 연결 시 쿼리 파라미터에서 token 값을 가져오기
        query_string = parse_qs(scope["query_string"].decode())
        token = query_string.get("token", None)

        if token:
            # 토큰이 존재하면 사용자 인증
            scope['user'] = await get_user(token[0])
        else:
            # 토큰이 없으면 AnonymousUser 할당
            scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)
