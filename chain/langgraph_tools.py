from typing import List
from decimal import Decimal

from langchain_core.runnables import ensure_config
from langchain_core.tools import tool
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from products.models import Product, Order, OrderItem


@tool
def fetch_user_information(user_id):
    """
    Fetch user information
    This function retrieves user information from the database
    """
    print("-"*77)
    print("fetch_user_information 진입")
    # config = ensure_config()  # Fetch from the context
    # configuration = config.get("configurable", {})
    # user_id = configuration.get("user_id", None)
    # print("config\n", config)
   
    return user_id


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
    제품의 라벨이나 신발박스가 훼손된 경우
    수제화 등 주문제작 상품의 경우
    오염물이 다르나 오염이 확실한 반품의 경우
    기간내에 상품을 보내주시고 교환/반품이 어려울정도로 훼손되어 보내주셨을 경우
    """
    return temp_info


def fetch_product_list():
    """
    Fetchs a list of products.
    This function retrieves and displays a list of products. 
    """

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
def get_product_list():
    """
    Gets a list of products.
    This function retrieves and displays a list of products. 
    """

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
def create_order(user_id: int, items :list[dict[str, str | int | float]]):
    """
    Places a new order.
    This function processes a new order request and confirms

    Args:
        user_id (int): The ID of the user placing the order.
        items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
            - "product_name": The name of the product (str)
            - "quantity": The quantity of the product (int)
            - "price": The price of the product (float)

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
def change_order(order_id: int, items: list[dict[str, str | int | float]]):
    """
    Modifies an existing order.
    This function allows the user to change details of an existing

    Args:
        order_id (int)
        items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
            - "product_name": The name of the product (str)
            - "quantity": The quantity of the product (int)
            - "price": The price of the product (float)
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
def cancel_order():
    """
    Cancels an existing order.
    This function processes the cancellation of an existing order
    """
    return "주문 취소 완료"

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
def fetch_change_order():
    """
    Views the details of a modified order.
    This function retrieves and returns the details of the changes made to an order.
    """
    return "주문 변경 조회 완료"

@tool
def fetch_cancel_order():
    """
    Views the details of a canceled order.
    This function retrieves and returns the details of a canceled order.
    """
    return "주문 취소 조회 완료"


@tool
def ask_how_to_change(selected_orders):
    """
    Asks customer how to change existing order the one selected 
    """
    return f"{selected_orders}"


@tool
def request_approval():
    """
    Requests customer confirm the task to be processed
    """
    return "고객의 요청을 정리하여 제시하고, 이 정리가 맞는지 확인하는 메시지를 작성해줘."


# user_request.py로 옮기길 GPT는 제안
from langchain_core.pydantic_v1 import BaseModel, Field

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


class TodDsplayUserOrder(BaseModel):
    """Transfers work to a specialized assistant to display user's orders."""

    request: str = Field(description="Any necessary follow-up messages display_user_order node should clarify before proceeding.")


class TodRequestApproval(BaseModel):
    """Transfers work to a specialized assistant to request user's approval"""
    selected_order : str = Field(description="고객이 선택한 기존 주문 내역")
    customer_request: str = Field(description="고객의 요청 사항")
    message_to_be_approved: str = Field(description="고객에게 내용 확인을 요청하는 메시지. 고객이 선택한 기존 주문 내역과 고객의 요청 사항을 모두 포함.")
