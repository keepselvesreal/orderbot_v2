from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from django.contrib.auth.models import User
from django.db.models import Prefetch
from django.db import transaction
from typing import Dict, Tuple
from django.db import transaction

from products.models import Order, Product, OrderItem, OrderStatus


@tool
def get_recent_orders_by_status(user_id, status):
    """
    Retrieve the three most recent orders with a specific status for the given user.
    """

    user = User.objects.get(id=user_id)

    recent_orders = Order.objects.filter(
        user=user,
        order_status=status,
    ).prefetch_related(
        Prefetch('status_changes', queryset=OrderStatus.objects.filter(status=status))
    ).order_by('-created_at')[:3]

    print("recent_orders: ", recent_orders)
    return [order.to_dict() if hasattr(order, 'to_dict') else {
        "id": order.id,
        "user_id": order.user.id,
        "created_at": order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        "order_status": order.order_status,
        "order_items": [{
            "product_name": item.product.product_name,
            "quantity": item.quantity,
            "price": float(item.price)
        } for item in order.order_items.all()]
    } for order in recent_orders]
    
tools = [get_recent_orders_by_status]

def determine_tool_usage(msg: AIMessage) -> Runnable:
    """Determine whether to use the tool based on the given condition."""
    print(msg)
    if msg.additional_kwargs: 
        tool_map = {tool.name: tool for tool in tools}
        tool_calls = msg.tool_calls.copy()
        for tool_call in tool_calls:
            tool_call["output"] = tool_map[tool_call["name"]].invoke(tool_call["args"])
        print("도구 출력 결과: ", tool_call["output"])
        return str(tool_call["output"]) # 테스트
    else:
        return msg.content
    
    
def get_completed_orders(dict):
    user_id = dict["user_id"]
    return Order.objects.filter(user_id=user_id, order_status='order')

def get_payment_completed_orders(dict):
    user_id = dict["user_id"]
    return Order.objects.filter(user_id=user_id, order_status='payment_completed')

def get_changed_orders(dict):
    user_id = dict["user_id"]
    return Order.objects.filter(user_id=user_id, order_status='order_changed')

def get_canceled_orders(dict):
    user_id = dict["user_id"]
    return Order.objects.filter(user_id=user_id, order_status='order_canceled')



def create_order(user: User, product_quantities: Dict[int, int]) -> Tuple[Order, float]:
    with transaction.atomic():
        # 주문 생성
        order = Order.objects.create(user=user)
        
        # 주문 상품 생성
        total_price = 0.0
        for product_id, quantity in product_quantities.items():
            product = Product.objects.get(id=product_id)
            price = product.price * quantity / product.quantity  # 상품 가격 계산
            OrderItem.objects.create(order=order, product=product, quantity=quantity, price=price)
            total_price += price
        
        # 주문 상태 생성 (OrderStatus는 시그널 핸들러에 의해 자동 생성/업데이트)
        # OrderStatus.objects.create(order=order, status='order')
        
        return order, total_price

def change_order_status(order_id: int, new_status: str) -> Order:
    with transaction.atomic():
        order = Order.objects.get(id=order_id)
        # 주문 상태 업데이트
        order.order_status = new_status
        order.save()
        
        # 주문 상태 생성 (OrderStatus는 시그널 핸들러에 의해 자동 생성/업데이트)
        # OrderStatus.objects.create(order=order, status=new_status)
        
        return order

def cancel_order(order_id: int) -> Order:
    with transaction.atomic():
        order = Order.objects.get(id=order_id)
        # 주문 상태를 'order_canceled'로 변경
        order.order_status = 'order_canceled'
        order.save()
        
        # 주문 상태 생성 (OrderStatus는 시그널 핸들러에 의해 자동 생성/업데이트)
        # OrderStatus.objects.create(order=order, status='order_canceled')
        
        return order
