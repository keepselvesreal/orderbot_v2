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
        order_id = text_data_json.get("orderId", None)
        order_details = text_data_json.get("orderDetails", None)
        message = text_data_json["message"]
        if order_id and order_details:
            message = order_details
        print("="*70)
        print("order_id\n",order_id)

        response_message = self.orderbot_response(user_id, message, order_id)
        now = timezone.now()
        if "confirm_message" in response_message:
            print("="*70)
            print("confirm_message\n", response_message["confirm_message"])
            if response_message["execution_confirmation"].content == "yes":
                print("="*70)
                print("execution_confirmation == yes!")
                response = handle_order_change_chain.invoke(
                    {"input": response_message["input"],
                     "order_id": response_message["order_id"]}
                )
                if isinstance(response, Order):
                    print("Order 객체 출력")
                    response = response.to_dict()
                elif isinstance(response, OrderDetails):
                    print("OrderDetails 객체 출력")
                    response = response.dict()  # Pydantic 모델을 dict로 변환
                print("response\n", response)
            else:
                response = response_message["confirm_message"].content
            self.send(text_data=json.dumps(
                    {"message": response,
                    "confirm_message": True,
                    "order_id": response_message["order_id"], 
                    "datetime": now.isoformat(),
                    "user": self.user.username,
                    }
                ))
        else:
            # response_message가 문자열인 경우 JSON으로 파싱
            if isinstance(response_message, str):
                try:
                    response_message = json.loads(response_message)
                except json.JSONDecodeError:
                    # JSON 파싱 실패시 그대로 사용
                    pass

            # response_message가 AIMessage인 경우 처리
            elif isinstance(response_message, AIMessage):
                response_message = {
                    "content": response_message.content,
                    "response_metadata": response_message.response_metadata
                }

            elif isinstance(response_message, dict) and "recent_orders" in response_message:
                recent_orders = response_message["recent_orders"]
                self.send(text_data=json.dumps(
                    {"recent_orders": recent_orders, 
                    "datetime": now.isoformat(),
                    "user": self.user.username,
                    }
                ))
            else:
                self.send(text_data=json.dumps(
                    {"message": json.dumps(response_message),  # JSON 문자열로 변환
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
            elif isinstance(response, AIMessage):
                print("AIMessage 객체 처리 구간 진입")
                response = response.content
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
