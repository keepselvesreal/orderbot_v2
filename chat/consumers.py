import json
import uuid
from datetime import datetime, timedelta, date as dt_date

from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from langchain_core.messages import ToolMessage
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework_simplejwt.authentication import JWTAuthentication

from chain.langgraph_graphs import orderbot_graph
from chain.langgraph_tools import fetch_product_list, fetch_product_list2
from products.models import Product, Order, OrderStatus

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

        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        user_id = text_data_json["userId"]
        order_id = text_data_json.get("orderId")
        orders = text_data_json.get("orders")
        selected_order = text_data_json.get("orderDetails")
        ordered_products = text_data_json.get("orderedProducts")
        start_date = text_data_json.get("startDate")
        start_date = self.parse_date(start_date) if start_date else None
        end_date = text_data_json.get("endDate")
        print("start_date, end_date: ", start_date, end_date)
        end_date = self.parse_date(end_date) if end_date else None
        order_status = text_data_json.get("orderStatus")
        # datetime = text_data_json.get("datetime") # 사용자 주문 요청 시간이 아닌 db에서 주문 생성 시 시간을 주문 시간으로 간주.
        
        if message == "show_products":
            self.send_product_list()
            return # 통신 종료
        elif message == "get_all_orders":
            self.get_all_orders(start_date, end_date)
            return
        elif message == "get_order_by_status":
            self.get_order_by_status(order_status, start_date, end_date)
            return 
        elif message == "create_order":
            self.create_order(user_id, ordered_products)
            return
        elif message == "order_to_change":
            order_change_type = "order_changed"
            self.get_changeable_orders(order_change_type, start_date, end_date)
            return 
        elif message == "order_changed":
            self.send_product_list(order_id)
            return
        elif message == "change_order":
            self.change_order(order_id, ordered_products)
            return 
        elif message == "order_to_cancel":
            order_change_type = "order_canceled"
            self.get_changeable_orders(order_change_type, start_date, end_date)
            return
        elif message == "order_canceled":
            self.cancel_order(order_id)
            return 

        print("order_id: ", order_id)
        print("selected_order\n", selected_order)
        # 브라우저에서 주문 아이디 선택한 경우
        if order_id:
            orderbot_graph.update_state(config, {"orders": None})
                                                 
            message = f"selected_order: {selected_order}"


        # 사용자 확인 필요한 도구 사용 여부 확인 위한 플래그 변수
        self.confirm_message = text_data_json.get("confirmMessage")
        print("self.confirm_message: ", self.confirm_message)
        self.tool_call_id = text_data_json.get("toolCallId")

        # 사용자 확인 필요한 도구 사용하지 않을 때의 출력
        if "confirmMessage" not in text_data_json:
            output = orderbot_graph.invoke({"messages": ("user", message),
                                            "user_info": user_id,
                                            },
                                            config)
            orders = output.get("orders")
        else:
            # 사용자 확인 필요한 도구 사용할 때의 출력
            print("-"*70)
            print("승인 메시지 확인 구간 진입")
            if message == "y":
                # 도구 사용 승인 했을 때의 출력
                print("승인 메시지 확인")
                output = orderbot_graph.invoke(
                    None,
                    config,
                )
                print()
            else:
                # 도구 사용 승인하지 않았을 때의 출력
                output = orderbot_graph.invoke(
                    {
                        "messages": [
                            ToolMessage(
                                tool_call_id=self.tool_call_id,
                                content=f"API call denied by user. Reasoning: '{message}'. Cㄴontinue assisting, accounting for the user's input.",
                            )
                        ]
                    },
                    config,
                )
        print("-"*70)
        print("model output\n", output)
        response = output["messages"][-1].content
        print("response\n", response)
        now = timezone.now()
        
        snapshot = orderbot_graph.get_state(config)
        # print("snapshot\n", snapshot)

        # 사용자 확인 필요한 도구 사용 경우
        if snapshot.next:
            print("-"*70)
            print("snapshot.next 존재")
            print("output['messages'][-1]\n",  output["messages"][-1])
            self.confirmation_message = True
            self.tool_call_id = output["messages"][-1].tool_calls[0]["id"]
            response = "작업을 승인하시려면 y를 입력하시고, 거부하신다면 변경 사유를 알려주세요!"
            
            self.send(text_data=json.dumps(
            {"user": self.user.username,
             "message": response,
             "datetime": now.isoformat(),
             "confirm_message": self.confirmation_message,
             "tool_call_id": self.tool_call_id,
             },
             ensure_ascii=False
             ))
        # 사용자 확인 필요한 도구 사용하지 않는 경우
        else:
            print("snapshot.next 존재 X")
            # 사용자 주문 내역이 조회된 경우
            if orders:
                print("orders 존재 시 처리 구간 진입")
                print("orders\n", orders)
                # 주문 선택하지 않은 경우
                if order_id is None:
                    response = "지난 주문 내역은 아래와 같습니다."
                self.send(text_data=json.dumps(
                    {"user": self.user.username,
                    "message": response,
                    "datetime": now.isoformat(),
                    "recent_orders": orders, 
                    },
                ensure_ascii=False
                ))
            else:
                self.send(text_data=json.dumps(
                    {"user": self.user.username,
                    "message": response,
                    "datetime": now.isoformat(),
                    },
                    ensure_ascii=False
                    ))
                
    def send_product_list(self, order_id=None):
        products = fetch_product_list2()
        if order_id:
            message = "주문을 어떻게 변경하실 건가요?\n아래 메뉴 목록에서 새로 주문해주세요."
        else:
            message = "다음은 메뉴 목록입니다."
        self.send(text_data=json.dumps({
            "user": self.user.username,
            "message": message,
            "datetime": timezone.now().isoformat(),
            "products": json.loads(products),
            "order_id": order_id
        }))

    def parse_date(self, date_str):
        print("-"*70)
        print("parse_date 진입")
        print("date_str: ", date_str)
        try:
            # Splitting the date string into parts
            parts = date_str.split('-')
            if len(parts) != 3:
                raise ValueError("Invalid date format. Expected YYYY-MM-DD or MM-DD format.")

            year, month, day = map(int, parts)

            # Creating a naive datetime object
            naive_date = datetime(year, month, day)

            # Making it aware of the current timezone
            aware_date = timezone.make_aware(naive_date, timezone.get_current_timezone())

            return aware_date.date()
        except ValueError as e:
            print(f"ValueError occurred: {e}")
            return None

    
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

    def get_user_from_jwt(self):
        try:
            token = None
            print("self.scope['headers']", self.scope['headers'])
            if 'Authorization' in self.scope['headers']:
                # 예시: Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
                auth_header = self.scope['headers']['Authorization'][0].decode('utf-8')
                print("auth_header: ", auth_header)
                token = auth_header.split(' ')[1]  # 'Bearer <token>'에서 <token> 부분 추출
            
            if token:
                authentication = JWTAuthentication()
                validated_token = authentication.get_validated_token(token)
                user = authentication.get_user(validated_token)
                return user
            else:
                print("JWT 토큰이 없습니다.")
                return None
        except Exception as e:
            print(f"JWT 인증 오류: {e}")
            return None
    
