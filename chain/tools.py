from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from django.contrib.auth.models import User
from django.db.models import Prefetch
from django.db import transaction
from typing import Tuple
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
import json
import os
from django.shortcuts import get_object_or_404

from products.models import Order, Product, OrderItem, OrderStatus
from .parsers import CreateOrderData


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


def create_order(data: CreateOrderData) -> Tuple[Order, Decimal]:
    print("="*70)
    print("create_order 진입")
    
    with transaction.atomic():
        # User 객체 가져오기
        user = User.objects.get(id=data.user_id)
        
        # 주문 생성
        order = Order.objects.create(user=user)
        
        # 주문 상품 생성
        total_price = Decimal('0.00')
        for item in data.items:
            product = Product.objects.get(product_name=item.product_name)
            OrderItem.objects.create(order=order, product=product, quantity=item.quantity, price=item.price)
            # total_price += item.price * item.quantity
            total_price += Decimal(item.price) * Decimal(item.quantity)
        
        # 주문 상태 생성 (OrderStatus는 시그널 핸들러에 의해 자동 생성/업데이트)
        # OrderStatus.objects.create(order=order, status='order')
        
        # return order, total_price 정상 동작 확인했으나 다른 함수와 통일 위해 total_price 삭제
        output = {"result": order, "execution": "yes"}
        # return order
        return output
    

def update_order(order_data):
    print("="*70)
    print("update_order 진입")
    try:
        # Pydantic 모델인 OrderDetails 객체를 딕셔너리로 변환
        order_data = order_data.dict() if hasattr(order_data, "dict") else order_data

        # Transaction을 사용하여 원자성을 보장
        with transaction.atomic():
            # 주문을 가져옴
            order = Order.objects.get(id=order_data['id'])
            # 주문 상태 업데이트
            order.order_status = order_data['order_status']
            order.save()

            # 기존 주문 항목 삭제 -> 삭제 대신 주문 상태 변경으로 수정하기
            OrderItem.objects.filter(order=order).delete()

            # 새로운 주문 항목 추가
            for item_data in order_data['items']:
                product = Product.objects.get(product_name=item_data['product_name'])
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
            # return {"status": "success", "message": "Order updated successfully"}
            {"result": "Order updated successfully", "execution": "yes"}
    except ObjectDoesNotExist as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}



def change_order_status(order_id: int, new_status: str) -> Order:
    with transaction.atomic():
        order = Order.objects.get(id=order_id)
        # 주문 상태 업데이트
        order.order_status = new_status
        order.save()
        
        # 주문 상태 생성 (OrderStatus는 시그널 핸들러에 의해 자동 생성/업데이트)
        # OrderStatus.objects.create(order=order, status=new_status)
        
        return order


def cancel_order(data: dict) -> dict:
    print("="*70)
    print("cancel_order 진입")

    order_id = data["order_id"]
    
    try:
        with transaction.atomic():
            order = Order.objects.get(id=order_id)
            # 주문 상태를 'order_canceled'로 변경
            order.order_status = 'order_canceled'
            order.save()
            
            # 주문 상태 생성 (OrderStatus는 시그널 핸들러에 의해 자동 생성/업데이트)
            # OrderStatus.objects.create(order=order, status='order_canceled')
            
            output = {"result": order, "execution": "yes"}
            # return order
            return output
    except Order.DoesNotExist:
        raise ValueError(f"Order with ID {order_id} does not exist")


def fetch_recent_orders(dict):
    print("="*70)
    print("fetch_recent_orders 진입")

    user_id = dict["user_id"]
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
        print("recent orders\n", recent_orders)
        return {"recent_orders": recent_orders}
    except ObjectDoesNotExist:
        return []
    

def fetch_order_details(dict):
    order_id = dict["order_id"]
    # 특정 order_id에 해당하는 주문 객체를 조회
    order = get_object_or_404(Order, id=order_id)
    
    # 주문 객체를 사전 형태로 변환
    order_dict = order.to_dict()
    
    # 해당 주문에 포함된 모든 주문 아이템 조회
    order_items = OrderItem.objects.filter(order=order)
    
    # 주문 아이템들을 사전 형태로 변환하여 추가
    order_dict["items"] = [
        {
            "product_name": item.product.product_name,
            "quantity": item.quantity,
            "price": float(item.price)
        }
        for item in order_items
    ]
    
    return order_dict


def fetch_products(dict):
    print("="*70)
    print("fetch_products 진입")

    base_dir = os.path.dirname(__file__)
    # products.json 파일의 절대 경로를 구합니다
    file_path = os.path.join(base_dir, 'files', 'products.json')
    
    with open(file_path, 'r', encoding='utf-8') as file:
        products = json.load(file)

    return products