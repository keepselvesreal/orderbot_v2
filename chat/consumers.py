import json
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
import os

from chain.chains import full_chain # chain_with_tools_n_history
from products.models import Order, OrderItem


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        print(self.user)
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        print(text_data)
        text_data_json = json.loads(text_data)
        user = text_data_json["user_id"]
        order_id = text_data_json.get("order_id", None)
        message = text_data_json["message"]

        if "주문 취소" in message:
            recent_orders = self.get_recent_orders(user)
            now = timezone.now()
            self.send(text_data=json.dumps(
                {"recent_orders": recent_orders, 
                 "datetime": now.isoformat(),
                 "user": self.user.username} # User Object인 듯
                ))
        else:
            response_message = self.orderbot_response(user, message)
            now = timezone.now()
            
            self.send(text_data=json.dumps(
                {"message": response_message, 
                "datetime": now.isoformat(),
                "user": self.user.username,
                "order_id": order_id} # User Object인 듯
                ))
        
    def orderbot_response(self, user, message):
        # products.json 파일의 경로 설정
        current_directory = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(current_directory, '..', 'chain', 'files', 'products.json')

        # JSON 파일 읽어오기
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            products = json.load(json_file)

        try:
            response = full_chain.invoke(
                {"user_id": user, "input": message, "products": products},
                config={"configurable": {"session_id": "test_240514-3"}}
            )
            print("full chain 출력: ", response)
            response = response[0]
            print("response[0]: ", response, type(response))
            if isinstance(response, QuerySet):
                print("QuerySet 처리 구간 진입")
                print("response: ", response)
                response = [order.to_dict() for order in response]
            elif hasattr(response, "to_dict"):
                response = response.to_dict()
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
        
    def get_recent_orders(self, user_id):
        # user_id를 사용하여 최근 주문 내역을 가져옵니다.
        try:
            orders = Order.objects.filter(user_id=user_id).order_by('-created_at')[:5]
            recent_orders = []
            for order in orders:
                order_items = OrderItem.objects.filter(order=order)
                items_details = [
                    {
                        "product_name": item.product.product_name,
                        "quantity": item.quantity,
                        "price": float(item.price)  # Decimal을 float으로 변환
                    } for item in order_items
                ]
                recent_orders.append({
                    "id": order.id,
                    "created_at": order.created_at.isoformat(),
                    "order_status": order.order_status,
                    "items": items_details
                })
            print("recent orders -> ", recent_orders)
            return recent_orders
        except ObjectDoesNotExist:
            return []
