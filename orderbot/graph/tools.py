from langchain_core.tools import tool
import json
from langchain_core.pydantic_v1 import BaseModel, Field
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from product.models import Order, Product, OrderStatus

@tool
def fetch_user_information(user_id):
    """
    Fetch user information
    This function retrieves user information from the database
    """
    print("-"*77)
    print("fetch_user_information 진입")
   
    return user_id


@tool
def get_all_orders(user_id):
        """
        Retrieves all orders for a specific user within an optional date range.
        
        Args:
            user_id (int): The ID of the user whose orders are to be retrieved.
            start_date (str, optional): The start date to filter orders in the format 'YYYY-MM-DD'. Defaults to None.
            end_date (str, optional): The end date to filter orders in the format 'YYYY-MM-DD'. Defaults to None.
        
        Returns:
            QuerySet: A QuerySet of Order objects.
        """
        print("-"*70)
        print("get_all_orders 진입")
        
        orders = Order.objects.filter(user__id=user_id).all()
        
        
        orders_data = [order.to_dict() for order in orders]
        orders_json = json.dumps(orders_data, ensure_ascii=False)
        return orders_json


@tool
def get_change_order(user_id):
    """
    Views the details of a modified order.
    
    This function retrieves and returns the details of the changes made to an order.
    
    Args:
        user_id (int): The ID of the user whose modified orders are to be retrieved.
    
    Returns:
        dict: A dictionary containing the details of the modified orders.
    """
    print("-"*77)
    print("get_change_order 진입")

    try:
        modified_orders = Order.objects.filter(user_id=user_id, order_status='order_changed')
        if not modified_orders.exists():
            return {"message": "No modified orders found for the user."}
        
        orders_data = [order.to_dict() for order in modified_orders]
        return orders_data
    
    except Exception as e:
        return {"error": str(e)}


@tool
def get_cancel_order(user_id):
    """
    Views the details of a canceled order.
    
    This function retrieves and returns the details of a canceled order.
    
    Args:
        user_id (int): The ID of the user whose canceled orders are to be retrieved.
    
    Returns:
        dict: A dictionary containing the details of the canceled orders.
    """
    print("-"*77)
    print("get_cancel_order 진입")
    
    try:
        canceled_orders = Order.objects.filter(user_id=user_id, order_status='order_canceled')
        if not canceled_orders.exists():
            return {"message": "No canceled orders found for the user."}
        
        orders_data = [order.to_dict() for order in canceled_orders]
        orders_json = json.dumps(orders_data, ensure_ascii=False)
        return orders_json
    
    except Exception as e:
        return {"error": str(e)}
    

class CompleteOrEscalate(BaseModel):
    """A tool to mark the current task as completed and/or to escalate control of the dialog to the main assistant,
    who can re-route the dialog based on the user's needs."""

    cancel: bool = True
    reason: str

    class Config:
        schema_extra = {
            "example": {
                "cancel": True,
                "reason": "User changed their mind about the current task.",
            },
            "example 2": {
                "cancel": True,
                "reason": "I have fully completed the task.",
            },
            "example 3": {
                "cancel": False,
                "reason": "I need to use the tool to place a new order.",
            },
        }


@tool
def lookup_policy(message: str):
    """
    Consult the company policies regarding product exchanges and refunds.
    Use this function to check the company policies before proceeding with an exchange or refund.
    """
    temp_info = """
    교환/반품 안내

    제품수령 후 7일 이내 교환/반품 가능합니다.
    상품 하자 이외의 사이즈/색상 변경은 단순 변심에 의한 교환/반품이 불가능합니다.
    이미지를 보시는 기기의 성상차이나 색상, 사이즈 등 개인의 성호도에 따라 달리 느껴질 수 있습니다.
    
    교환/반품이 불가능한 경우
    제품의 라벨이나 박스가 훼손된 경우
    주문제작 상품의 경우
    오염이 확실한 반품의 경우
    교환/반품이 어려울정도로 훼손되어 보내주셨을 경우
    """
    print("-"*77)
    print("lookup_policy 진입")

    return temp_info


@tool
def fetch_product_list():
    """
    Fetchs a list of products.
    This function retrieves and displays a list of products. 
    """
    print("-"*70)
    print("fetch_product_list 진입")

    product_list = """
    [
        {
            "product_name": "떡케익5호",
            "quantity": 1,
            "price": 54000
        },
        {
            "product_name": "무지개 백설기 케익",
            "quantity": 1,
            "price": 51500
        },
        {
            "product_name": "미니 백설기",
            "quantity": 35,
            "price": 31500
        },
        {
            "product_name": "개별 모듬팩",
            "quantity": 1,
            "price": 13500
        }
    ]
    """
    return product_list


@tool
def create_order(user_id: int, items :list):
    """
    Places a new order.
    This function processes a new order request and confirms it by creating an order and its related items in the database.

    Args:
        user_id (int): The ID of the user placing the order.
        items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
            - "product_name" (str): The name of the product.
            - "quantity" (int): The quantity of the product.
            - "price" (float): The price of the product.

    Example:
        items = [
            {"product_name": "떡케익5호", "quantity": 2, "price": 54000.0},
            {"product_name": "무지개 백설기 케익", "quantity": 1, "price": 51500.0}
        ]
    """
    print("-"*70)
    print("create_order 진입")
    
    with transaction.atomic():
        # User 객체 가져오기
        user = User.objects.get(id=user_id)
        
        # 주문 생성
        order = Order.objects.create(user=user)
        
        # 주문 상품 생성
        total_price = Decimal('0.00')
        for item in items:
            product = Product.objects.get(product_name=item["product_name"])
            # OrderItem.objects.create(order=order, product=product, quantity=item["quantity"], price=item["price"])
            order.order_items.create(product=product, quantity=item["quantity"], price=item["price"])
            total_price += Decimal(item["price"]) * Decimal(item["quantity"])

        return order
    

@tool
def fetch_recent_order(user_id):
    """
    Fetches the details of a specific order.
    This function retrieves and returns the details of an order.
    
    Args:
    user_id (int): The unique identifier of the user whose recent order details are to be fetched.

    Returns:
        dict: A dictionary containing the details of the most recent order placed by the specified user.
    """
    print("-"*77)
    print("fetch_recent_order 진입")
    print("전달 받은 인자: ", user_id)

    try:
        orders = Order.objects.filter(user__id=user_id).order_by('-created_at')[:5]
        print("orders\n", orders)
        recent_orders = []
        for order in orders:
            order_items = order.order_items.all()
            print("order_items\n", order_items)
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
        
        return recent_orders
    except ObjectDoesNotExist:
        return "ObjectDoesNotExist" # 임시


@tool
def change_order(order_id: int, items: list):
    """
    Modifies an existing order.
    This function allows the user to change details of an existing

    Args:
        order_id (int)
        items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
            - "product_name": The name of the product (str)
            - "quantity": The quantity of the product (int)
            - "price": The price of the product (float)

    Example:
        items = [
            {"product_name": "떡케익5호", "quantity": 2, "price": 54000.0},
            {"product_name": "무지개 백설기 케익", "quantity": 1, "price": 51500.0}
        ]
    """
    print("="*70)
    print("change_order 진입")

    try:
        # Transaction을 사용하여 원자성을 보장
        with transaction.atomic():
            # 주문을 가져옴
            order = Order.objects.get(id=order_id)

            # 기존 주문 항목 삭제
            order.order_items.all().delete()

            # 새로운 주문 항목 추가
            for item_data in items:
                product = Product.objects.get(product_name=item_data['product_name'])
                order.order_items.create(  # OrderItem.objects.create 대신 사용
                    product=product,
                    quantity=item_data['quantity'],
                    price=Decimal(item_data['price'])
                )
            
            order.order_status = 'order_changed'
            order.save()
            
            return {"message": "Order updated successfully"}
    except ObjectDoesNotExist as e:
        # 주문 또는 제품이 존재하지 않는 경우의 예외 처리
        return {"message": str(e)}

    except Exception as e:
        # 일반적인 예외 처리
        return {"message": str(e)}


@tool
def cancel_order(order_id):
    """
    Cancels an existing order.
    
    Args:
        order_id (int): The ID of the order to be canceled.
    
    Returns:
        str: A message indicating the result of the cancellation process.
    """
    print("="*70)
    print("cancel_order 진입")

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
            )
            
            if not created:
                return f"주문 {order_id}에 대한 취소 기록이 이미 존재합니다."
            
            return f"주문 {order_id}가 취소되었습니다."
            
    except Order.DoesNotExist:
        return f"주문 {order_id}를 찾을 수 없습니다."

    except Exception as e:
        return f"주문 취소 중 오류가 발생했습니다: {str(e)}"
    

class ToOrderInquiryAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle order queries."""

    order_id: int = Field(description="The ID of the order to query.")
    request: str = Field(description="Any necessary follow-up questions the querying assistant should clarify before proceeding.")


# order_request.py로 옮길 것을 제안
class ToOrderAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle new order creation."""

    user_id: int = Field(description="The unique identifier of the user")
    request: str = Field(description="Any necessary follow-up questions the order assistant should clarify before proceeding.")


class ToOrderChangeAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle order change."""

    user_id: int = Field(description="The unique identifier of the user")
    request: str = Field(description="Any necessary follow-up questions the order change assistant should clarify before proceeding.")


class ToOrderCancelAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle order cancel."""

    user_id: int = Field(description="The unique identifier of the user")
    request: str = Field(description="Any necessary follow-up questions the order cancel assistant should clarify before proceeding.")


class ToRequestOrderConfirmation(BaseModel):
    """Transfers work to a specialized assistant to request the user's approval for creating an order."""
    product_list: str = Field(description="판매 중인 상품 목록")
    customer_order_request: str = Field(description="고객의 주문 요청 사항")
    message_to_be_confirmed: str = Field(description="고객의 주문 요청 내용에 대해 확인을 요청하는 메시지. 상품명과 상품 가격이 판매 중인 상품 목록과 일치해야 함.")


class ToHowToChange(BaseModel):
    """Transfers work to a specialized assistant to ask a user how to change selected order"""
    selected_order : str = Field(description="고객이 선택한 기존 주문 내역")


class ToRequestOrderChangeConfirmation(BaseModel):
    """Transfers work to a specialized assistant to request the user's approval for changing an order."""
    selected_order : str = Field(description="고객이 선택한 기존 주문 내역")
    customer_request: str = Field(description="고객의 요청 사항")
    new_order : str = Field(description="고객의 요청 사항이 반영된 새로운 주문")
    message_to_be_approved: str = Field(description="고객에게 내용 확인을 요청하는 메시지. 고객이 선택한 기존 주문 내역과 새로운 주문 모두 포함.")


class ToRequestOrderCancelConfirmation(BaseModel):
    """Transfers work to a specialized assistant to request the user's approval for canceling an order."""
    selected_order : str = Field(description="고객이 선택한 기존 주문 내역")
    customer_order_request: str = Field(description="고객의 요청 사항")
    message_to_be_confirmed: str = Field(description="고객에게 내용 확인을 요청하는 메시지. 고객이 선택한 기존 주문 내역과 고객의 요청 사항을 모두 포함.")