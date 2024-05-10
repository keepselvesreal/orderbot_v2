import json
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone

# 메시지 입력하면 채팅창에 나타나는 기능까지 구현
class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        print(self.user)
        self.accept()

    def disconnect(self):
        pass

    def receive(self, text_data):
        print(text_data)
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        now = timezone.now()
        print(message)
        self.send(text_data=json.dumps(
            {"message": message, 
             "datetime": now.isoformat(),
             "user": self.user.username} # User Object인 듯
            ))
