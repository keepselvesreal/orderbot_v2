import json
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
from langchain_core.messages import AIMessage

from chain.chains import input_dispatcher_chain, full_chain, handle_order_change_chain# chain_with_tools_n_history
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
        message = text_data_json["message"]
        user_id = text_data_json["userId"]
        order_id = text_data_json.get("orderId")
        self.request_type= text_data_json.get("requestType")
        self.confirm_message = text_data_json.get("confirmMessage") # connect에서 초기화하고 클라이언트에서 받지 않아도 될 듯
        self.approval_request = text_data_json.get("approvalRequest")

        if order_id and not self.approval_request:
            print("="*70)
            print("order_id 할당됨!\n", order_id)
            message = "해당 주문 선택"
            # message = ""
        
        response_message = self.orderbot_response(
            user_id=user_id, 
            message=message, 
            order_id=order_id,
            request_type = self.request_type,
            confirm_message=self.confirm_message,
        )
        now = timezone.now()

        self.send(text_data=json.dumps(
            {"user": self.user.username,
             "message": response_message,
             "datetime": now.isoformat(),
             "order_id": order_id,
             "request_type": self.request_type,
             "confirm_message": self.confirm_message,
             "approval_request": self.approval_request,
             },
             ensure_ascii=False
             ))
        
        self.request_type = None
        self.confirm_message = None
        self.approval_request = None
        print("="*70)
        print("self.confirm_message 초기화 ->", self.confirm_message)

        
    def orderbot_response(self, user_id, message, order_id=None, request_type=None, confirm_message=None):
        print("="*70)
        print("orderbot_response 진입")
        try:
            response = input_dispatcher_chain.invoke(
                {"user_id": user_id,
                 "input": message,
                 "order_id": order_id,
                 "confirm_message": confirm_message,
                 "request_type": request_type,
                 }
            )
            print("="*70)
            print("<full_chain response>\n", "type-> ", type(response), "\ncontent-> ", response)
            
            if isinstance(response, Order):
                response = response.to_dict()
                response = json.dumps(response)
            # 응답이 딕셔너리인 경우 JSON 문자열로 변환
            elif isinstance(response, QuerySet):
                return json.dumps([order.to_dict() for order in response])
            elif isinstance(response, dict):
                if "confirm_message" in response:
                    print("="*70)
                    print("confirm_message 키 존재")
                    print("confirm_message키 추출 전 response\n", response)
                    self.confirm_message = response["confirm_message"]
                    self.request_type = response["request_type"]
                    print("self.request_type 값 ->", self.request_type)
                    self.approval_request = True
                    # self.confirm_message = True
                    print("self.approval_request 값->", self.approval_request)
                    response = self.confirm_message

                response = json.dumps(response, ensure_ascii=False)
            
            print("="*70)
            print("<orderbot response>\n", "type-> ", type(response), "\ncontent-> ", response)
            return response
        except ObjectDoesNotExist:
            return json.dumps({"error": "User or order not found"})
        except Exception as e:
            return json.dumps({"error": str(e)})