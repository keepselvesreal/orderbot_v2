from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required


@login_required
def user_chat_room(request):
    try:
        print("user_pk: ", request.user.pk)
        return render(request, 'chat/room.html', {'user_id': request.user.pk}) 
    except:
        return HttpResponseForbidden()
