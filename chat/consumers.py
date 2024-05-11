import json
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone

from chain.chains import chain_with_tools_n_history

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
        user = text_data_json["user_id"]
        message = text_data_json["message"]
        response_message = self.orderbot_response(user, message)
        now = timezone.now()
        
        self.send(text_data=json.dumps(
            {"message": response_message, 
             "datetime": now.isoformat(),
             "user": self.user.username} # User Object인 듯
            ))
        
    def orderbot_response(self, user, message):
        try:
            response = chain_with_tools_n_history.invoke(
                {"user_id": user, "input": message},
                config={"configurable": {"session_id": "test_240511-1"}}
            )
            return response
        except Exception as e:
            return str(e)
