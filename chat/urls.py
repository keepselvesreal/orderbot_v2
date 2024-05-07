from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("room/", views.user_chat_room, name="user_chat_room"),
]