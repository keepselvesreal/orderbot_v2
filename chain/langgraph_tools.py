from langchain_core.tools import tool


@tool
def fetch_user_information(user_id: str):
    """
    Fetch user information
    This function retrieves user information from the database
    """
    print("-"*77)
    print("fetch_user_information 진입")
    print("user_id: ",user_id)
    temp_info = """
    name: nadle
    사용자 이름: nadle
    구매 일자: 2024.06.18
    구매 상품:
    무지개 백설기 (12,000원) 3개
    개별 모듬팩 (5,000원) 2개
    떡케익 (25,000원) 1개
    총 구매 금액: 71,000원
    """
    return temp_info


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


@tool
def order():
    """
    Places a new order.
    This function processes a new order request and confirms
    """
    return "주문 완료"

@tool
def change_order():
    """
    Modifies an existing order.
    This function allows the user to change details of an existing
    """
    return "주문 변경 완료"

@tool
def cancel_order():
    """
    Cancels an existing order.
    This function processes the cancellation of an existing order
    """
    return "주문 취소 완료"

@tool
def view_order(state):
    """
    Views the details of a specific order.
    This function retrieves and returns the details of an order.
    """
    from products.models import Order, OrderItem
    from django.core.exceptions import ObjectDoesNotExist
    user_id = state["user_info"]

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
        
        return recent_orders
    except ObjectDoesNotExist:
        return []
    # return "주문 조회 완료"

@tool
def view_change_order():
    """
    Views the details of a modified order.
    This function retrieves and returns the details of the changes made to an order.
    """
    return "주문 변경 조회 완료"

@tool
def view_cancel_order():
    """
    Views the details of a canceled order.
    This function retrieves and returns the details of a canceled order.
    """
    return "주문 취소 조회 완료"


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

# order_request.py로 옮길 것을 제안
class ToOrderInquiryAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle order queries."""

    order_id: int = Field(description="The ID of the order to query.")
    request: str = Field(description="Any necessary follow-up questions the querying assistant should clarify before proceeding.")

class ToOrderRequestAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle order placements, modifications, or cancellations."""

    order_id: int = Field(description="The ID of the order to update.")
    action: str = Field(description="The action to perform: 'order', 'change_order', 'cancel_order'.")
    request: str = Field(description="Any additional information or requests from the user regarding the order.")