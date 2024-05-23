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
        message = text_data_json["message"]
        user_id = text_data_json["userId"]
        order_id = text_data_json.get("orderId")
        order_details = text_data_json.get("orderDetails")
        self.confirm_message = text_data_json.get("confirmMessage")
        self.approval_request = text_data_json.get("approvalRequest")
        # self.execution_confirmation = text_data_json.get("executionConfirmation")
        

        if order_id and order_details and not self.approval_request:
            print("="*70)
            print("order_id 할당됨!\n", order_id)
            message = order_details
        else:
            print(f"조건 불충족: order_id={order_id}, order_details={order_details}")
        

        response_message = self.orderbot_response(
            user_id=user_id, 
            message=message, 
            order_id=order_id, 
            order_details=order_details,
            confirm_message=self.confirm_message,
            # execution_confirmation=self.execution_confirmation
        )
        now = timezone.now()

        self.send(text_data=json.dumps(
            {"user": self.user.username,
             "message": response_message,
             "datetime": now.isoformat(),
             "order_id": order_id,
             "confirm_message": self.confirm_message,
             "approval_request": self.approval_request
            #  "execution_confirmation": self.execution_confirmation,
             },
             ensure_ascii=False
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
                 }
            )
            print("="*70)
            print("<full_chain response>\n", "type-> ", type(response), "\ncontent-> ", response)
            
            # StrOutputParser() 추가 후에는 AIMessage 삭제해도 될 듯
            if isinstance(response, AIMessage):
                response = response.content
            elif isinstance(response, Order):
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