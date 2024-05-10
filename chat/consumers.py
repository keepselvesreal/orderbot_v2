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
        message = text_data_json["message"]
        response_message = self.orderbot_response(message)
        now = timezone.now()
        
        self.send(text_data=json.dumps(
            {"message": response_message, 
             "datetime": now.isoformat(),
             "user": self.user.username} # User Object인 듯
            ))
        
    def orderbot_response(self, message):
        response = chain_with_tools_n_history.invoke(
            {"input": message},
            config={"configurable": {"session_id": "test_240510-6"}}
        )
        return response
