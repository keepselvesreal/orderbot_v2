import json
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

from chain.chains import full_chain # chain_with_tools_n_history


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
            response = full_chain.invoke(
                {"user_id": user, "input": message},
                config={"configurable": {"session_id": "test_240514-3"}}
            )
            print("full chain 출력: ", response)
            if isinstance(response, QuerySet):
                response = [order.to_dict() for order in response]
            response = json.dumps(response)
            print("json.dumps() 출력: ", response)
            # response = summary_chain.invoke(
            #     {"input": response}
            # ).content
            return response
        except ObjectDoesNotExist:
            return json.dumps({"error": "User or order not found"})
        except Exception as e:
            return json.dumps({"error": str(e)})
