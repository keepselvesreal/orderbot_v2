import json
import uuid
from datetime import datetime

from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
from langchain_core.messages import HumanMessage, ToolMessage

from chain.langgraph_graphs import orderbot_graph
from chain.langgraph_tools import fetch_product_list, fetch_product_list2
from products.models import Product, Order, OrderStatus
from .utilities import process_message, execute_compiled_graph, dict_to_json

thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        # Todo: user_id로 대체 
        "passenger_id": "1089",
        # Checkpoints are accessed by thread_id
        "thread_id": thread_id,
    }
}

class ChatConsumer(WebsocketConsumer):
    SESSION_ID = "240606"

    def connect(self):
        self.user = self.scope["user"]
        print("self.user: ", self.user)
        self.confirmation_message = None
        self.tool_call_id = None
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        print("-"*70)
        print("receive 진입")
        print("클라이언트가 보낸 데이터\n", text_data)

        # text_data_json = json.loads(text_data)
        data_from_client = json.loads(text_data)
        print("data from client\n", data_from_client)
        message = data_from_client["message"]
        selected_order_id = data_from_client.get("orderId")
        selected_order = data_from_client.get("orderDetails")
        has_confirmation = data_from_client.get("confirmMessage")
        tool_call_id = data_from_client.get("toolCallId")
        user_id = data_from_client.get("userId") # 임시로
        
        is_precessed = process_message(self, message, data_from_client)
        if is_precessed: return

        print("selected_order_id: ", selected_order_id)
        print("selected_order\n", selected_order)
        # 브라우저에서 주문 아이디 선택한 경우
        if selected_order_id:
            orderbot_graph.update_state(config, {"orders": None})
                                                 
            message = f"selected_order: {selected_order}"

        # 사용자 확인 필요한 도구 사용 여부 확인 위한 플래그 변수
        if has_confirmation is None:
            message_object = HumanMessage(content=message)
            # message_object = ("user", message)
            output = execute_compiled_graph(
                compiled_graph=orderbot_graph, 
                config=config, 
                messages=message_object, 
                user_info=user_id
                )
        else:
            # 사용자 확인 필요한 도구 사용할 때의 출력
            print("-"*70)
            print("승인 메시지 확인 구간 진입")
            if message == "y":
                # 도구 사용 승인 했을 때의 출력
                print("승인 메시지 확인")
                output = execute_compiled_graph(compiled_graph=orderbot_graph, config=config)
            else:
                # 도구 사용 승인하지 않았을 때의 출력
                message_object = ToolMessage(
                    content=f"API call denied by user. Reasoning: '{message}'. Cㄴontinue assisting, accounting for the user's input.",
                    tool_call_id=tool_call_id,
                )
                output = execute_compiled_graph(
                    config=config,
                    message=message_object
                )
                
        print("-"*70)
        print("model output\n", output)
        response = output["messages"][-1].content
        print("response\n", response)
        order_history = output.get("orders")

        snapshot = orderbot_graph.get_state(config)

        # 사용자 확인 필요한 도구 사용 경우
        if snapshot.next:
            print("-"*70)
            print("snapshot.next 존재")
            print("output['messages'][-1]\n",  output["messages"][-1])
           
            has_confirmation = True
            tool_call_id = output["messages"][-1].tool_calls[0]["id"]
            response = "작업을 승인하시려면 y를 입력하시고, 거부하신다면 변경 사유를 알려주세요!"
            
            json_data = dict_to_json(
                user=self.user.username, 
                message=response,
                confirm_message=has_confirmation,
                tool_call_id=tool_call_id
                )
            
            self.send(text_data=json_data)
        # 사용자 확인 필요한 도구 사용하지 않는 경우
        else:
            print("snapshot.next 존재 X")
            # 사용자 주문 내역이 조회된 경우
            if order_history:
                print("order_history 존재 시 처리 구간 진입")
                print("order_history\n", order_history)
                # 주문 선택하지 않은 경우. 반면 order_id 있다면 특정 주문 선택한 경우이고, 이때 response는 이를 바탕으로 어떤 처리 진행하고 model이 응답 생성한 경우.
                if selected_order_id is None:
                    response = "지난 주문 내역은 아래와 같습니다."
                json_data = dict_to_json(
                    user=self.user.username, 
                    message=response, 
                    recent_orders=order_history
                    )
                self.send(text_data=json_data)
            else:
                json_data = dict_to_json(
                    user=self.user.username, 
                    message=response, 
                    )
                self.send(text_data=json_data)
                
    def send_product_list(self, selected_order_id=None):
        products = fetch_product_list2()
        if selected_order_id:
            message = "주문을 어떻게 변경하실 건가요?\n아래 메뉴 목록에서 새로 주문해주세요."
        else:
            message = "다음은 메뉴 목록입니다."
        self.send(text_data=json.dumps({
            "user": self.user.username,
            "message": message,
            "datetime": timezone.now().isoformat(),
            "products": json.loads(products),
            "order_id": selected_order_id
        }))
    
    def get_all_orders(self, start_date=None, end_date=None):
        print("-"*70)
        print("get_all_orders 진입")
        print("startdate / enddate: ", f"{start_date} / {end_date}")
        orders = Order.objects.all()
        if start_date and end_date:
            orders = orders.filter(created_at__date__range=[start_date, end_date])
        elif start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        elif end_date:
            orders = orders.filter(created_at__date__lte=end_date)
        
        orders_data = [order.to_dict() for order in orders]
        
        self.send(text_data=json.dumps({
            "user": self.user.username,
            "message": "전체 주문 목록입니다.",
            "fetched_orders": orders_data
        }))

    def get_order_by_status(self, order_status, start_date=None, end_date=None):
        print("-"*70)
        print("get_order_by_status 진입")
        print("startdate / enddate: ", f"{start_date} / {end_date}")
        orders = Order.objects.filter(order_status=order_status)
        if start_date and end_date:
            orders = orders.filter(created_at__date__range=[start_date, end_date])
        elif start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        elif end_date:
            orders = orders.filter(created_at__date__lte=end_date)
        
        orders_data = [order.to_dict() for order in orders]
        status_name = dict(OrderStatus.STATUS_CHOICES)[order_status]
        
        self.send(text_data=json.dumps({
            "user": self.user.username,
            "message": f"{status_name}인 주문 목록입니다.",
            "fetched_orders": orders_data
        }))

    def get_changeable_orders(self, order_change_type, start_date=None, end_date=None):
        print("-"*70)
        print("get_changeable_orders 진입")
        print("startdate / enddate: ", f"{start_date} / {end_date}")

        if order_change_type == "order_changed":
            message = "주문 변경이 가능한 주문 목록입니다."
        else:
            message = "주문 취소가 가능한 주문 목록입니다."
        
        orders = Order.objects.exclude(order_status="order_canceled")
        
        if start_date and end_date:
            orders = orders.filter(created_at__date__range=[start_date, end_date])
        elif start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        elif end_date:
            orders = orders.filter(created_at__date__lte=end_date)
        
        orders_data = [order.to_dict() for order in orders]
        
        self.send(text_data=json.dumps({
            "user": self.user.username,
            "message": message,
            "changeable_orders": orders_data,
            "order_change_type": order_change_type
        }))

    def create_order(self, user_id, ordered_products):
        try:
            print("-"*70)
            print("create_order 진입")
            print("ordered_products\n", ordered_products)
            
            user = User.objects.get(id=user_id)
            
            with transaction.atomic():
                order = Order.objects.create(user=user)
                
                total_price = Decimal('0.00')
                for ordered_product in ordered_products:
                    try:
                        product = Product.objects.get(product_name=ordered_product["productName"])
                    except ObjectDoesNotExist:
                        self.send(text_data=json.dumps({
                            'message': 'error',
                            'error': f'Product not found: {ordered_product["productName"]}'
                        }))
                        return

                    order.order_items.create(product=product, quantity=ordered_product["quantity"], price=Decimal(ordered_product["productPrice"]))
                    total_price += Decimal(ordered_product["productPrice"]) * Decimal(ordered_product["quantity"])

                # 응답 보내기 (선택 사항)
                self.send(text_data=json.dumps({
                    'message': 'order_confirmed',
                    'order_id': order.id,
                    'total_price': str(total_price)
                }))
        
        except ObjectDoesNotExist:
            self.send(text_data=json.dumps({
                'message': 'error',
                'error': 'User not found'
            }))
        
        except Exception as e:
            self.send(text_data=json.dumps({
                'message': 'error',
                'error': str(e)
            }))

    def change_order(self, order_id, ordered_products):
        try:
            print("-" * 70)
            print("change_order 진입")
            print("ordered_products\n", ordered_products)
            
            with transaction.atomic():
                # 주문 ID로 기존 주문을 가져옴
                try:
                    order = Order.objects.get(id=order_id)
                except ObjectDoesNotExist:
                    self.send(text_data=json.dumps({
                        'message': 'error',
                        'error': f'Order not found: {order_id}'
                    }))
                    return

                # 주문 상태를 변경
                order.order_status = 'order_changed'
                order.save()
                
                # 기존 주문 항목을 모두 삭제
                order.order_items.all().delete()
                
                total_price = Decimal('0.00')
                for ordered_product in ordered_products:
                    try:
                        product = Product.objects.get(product_name=ordered_product["productName"])
                    except ObjectDoesNotExist:
                        self.send(text_data=json.dumps({
                            'message': 'error',
                            'error': f'Product not found: {ordered_product["productName"]}'
                        }))
                        return

                    # 새로운 주문 항목 생성
                    order.order_items.create(product=product, quantity=ordered_product["quantity"], price=Decimal(ordered_product["productPrice"]))
                    total_price += Decimal(ordered_product["productPrice"]) * Decimal(ordered_product["quantity"])

                # 응답 보내기 (선택 사항)
                self.send(text_data=json.dumps({
                    'message': 'order_changed_confirmed',
                    'order_id': order.id,
                    'total_price': str(total_price)
                }))
        
        except ObjectDoesNotExist:
            self.send(text_data=json.dumps({
                'message': 'error',
                'error': 'Order not found'
            }))
        
        except Exception as e:
            self.send(text_data=json.dumps({
                'message': 'error',
                'error': str(e)
            }))

    def cancel_order(self, order_id):
        print("-"*70)
        print("cancel_order 진입")
        print("order_id: ", order_id)
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)
                
                # 주문을 '주문 취소' 상태로 변경
                order.order_status = 'order_canceled'
                order.save()
                
                # OrderStatus에 상태 변경 기록
                # UNIQUE constraint 오류 방지를 위해 get_or_create 사용
                order_status, created = OrderStatus.objects.get_or_create(
                    order=order,
                    status='order_canceled',
                    defaults={'changed_at': timezone.now()}
                )
                
                if not created:
                    print(f"주문 {order_id}에 대한 취소 기록이 이미 존재합니다.")
                
                # 성공적으로 취소되었음을 클라이언트에 알림
                self.send(text_data=json.dumps({
                    "user": self.user.username,
                    "message": f"주문 {order_id}가 취소되었습니다.",
                    "order_status": order.order_status,
                    "order_id": order_id
                }))
        except Order.DoesNotExist:
            self.send(text_data=json.dumps({
                "user": self.user.username,
                "message": f"주문 {order_id}를 찾을 수 없습니다.",
            }))
        except Exception as e:
            self.send(text_data=json.dumps({
                "user": self.user.username,
                "message": f"주문 취소 중 오류가 발생했습니다: {str(e)}",
            }))
    
