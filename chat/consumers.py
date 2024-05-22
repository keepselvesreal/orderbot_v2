import json
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
from langchain_core.messages import AIMessage

from chain.chains import full_chain, handle_order_change_chain# chain_with_tools_n_history
from products.models import Order, OrderItem
from chain.parsers import OrderDetails


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        print(self.user)
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        print("="*70)
        print("클라이언트가 전달한 데이터\n", text_data)
        text_data_json = json.loads(text_data)
        user_id = text_data_json["userId"]
        order_id = text_data_json.get("orderId")
        order_details = text_data_json.get("orderDetails")
        message = text_data_json["message"]

        if order_id and order_details:
            print("="*70)
            print("order_id 할당됨!\n",order_id)
            message = order_details
        

        response_message = self.orderbot_response(
            user_id=user_id, 
            message=message, 
            order_id=order_id, 
            order_details=order_details,
            confirm_message=text_data_json.get("confirmMessage"),
            execution_confirmation=text_data_json.get("executionConfirmation")
        )
        now = timezone.now()

        self.send(text_data=json.dumps(
            {"message": response_message["msg_type"],
             "datetime": now.isoformat(),
             "user": self.user.username}
             ))
        
        
    def orderbot_response(self, user_id, message, order_id=None, order_details=None, confirm_message=None, execution_confirmation=None):
        print("="*70)
        print("orderbot_response 진입")
        try:
            response = full_chain.invoke(
                {"user_id": user_id,
                 "input": message,
                 "order_id": order_id,
                 "order_details": order_details,
                 "confirm_message": confirm_message,
                 "execution_confirmation": execution_confirmation}
            )
            print("<orderbot response>\n", "type-> ", type(response), "\ncontent-> ", response)
            return response
        except ObjectDoesNotExist:
            return json.dumps({"error": "User or order not found"})
        except Exception as e:
            return json.dumps({"error": str(e)})