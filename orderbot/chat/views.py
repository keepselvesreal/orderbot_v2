from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseForbidden

@login_required
def user_chat_room(request):
    try:
        print("*"*77)
        print("user_chat_room 진입")
        print("user_pk: ", request.user.pk)
        return render(request=request, template_name="chat/room.html", context={"user_id": request.user.pk})
    except:
        return HttpResponseForbidden
