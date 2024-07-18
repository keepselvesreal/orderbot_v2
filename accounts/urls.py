from django.urls import path

from .views import UserDetailView

urlpatterns = [
    path('user/', UserDetailView.as_view(), name='user-detail'),
    # 다른 필요한 API URL 설정
]
