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
        print("="*70)
        print("클라이언트가 전달한 데이터\n", text_data)
        text_data_json = json.loads(text_data)
        user_id = text_data_json["userId"]
        order_id = text_data_json.get("orderId", None)
        order_details = text_data_json.get("orderDetails", None)
        message = text_data_json["message"]
        if order_id:
            message = order_details
        print("="*70)
        print("order_id\n",order_id)

        response_message = self.orderbot_response(user_id, message, order_id)
        now = timezone.now()
        if isinstance(response_message, str):
            response_message = json.loads(response_message)

        if "recent_orders" in response_message:
            recent_orders = response_message["recent_orders"]
            self.send(text_data=json.dumps(
            {"recent_orders": recent_orders, 
            "datetime": now.isoformat(),
            "user": self.user.username, # User Object인 듯
            }
            ))
        else:
            self.send(text_data=json.dumps(
                {"message": response_message, 
                "datetime": now.isoformat(),
                "user": self.user.username,
                }
                ))
        
    def orderbot_response(self, user_id, message, order_id):
        print("="*70)
        print("orderbot_response 진입")
        try:
            response = full_chain.invoke(
                {"user_id": user_id, 
                 "input": message, 
                 "order_id": order_id},
            )
            print("="*70)
            print("orderbot response\n", response)
            
            if isinstance(response, QuerySet):
                print("QuerySet 처리 구간 진입")
                print("response\n", response)
                response = [order.to_dict() for order in response]
            elif hasattr(response, "to_dict"):
                print("to_dict 메서드 보유 객체 처리 구간 진입")
                print("response\n", response)
                response = response.to_dict()
            # elif isinstance(response, Order):
            #     print("Order 객체 처리 구간 진입")
            #     response = response.to_dict()
            else:
                print("알 수 없는 response 타입\n", type(response))
            
            if not isinstance(response, (dict, list)):
                response = json.dumps(response)

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
        
    def handle_execution(self):
        pass
