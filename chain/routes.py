from langchain_core.runnables import RunnableLambda

from .tools import (
    get_completed_orders, 
    get_payment_completed_orders, 
    get_changed_orders, 
    get_canceled_orders,
    fetch_recent_orders, 
    cancel_order,
    )


def inquiry_types_route(info):
    print("="*70)
    print("inquiry_types_route 함수로 전달된 데이터 -> ", info)
    if "입금 완료" in info["inquiry_type"].content.lower():
        return RunnableLambda(get_payment_completed_orders)
    elif "주문 변경" in info["inquiry_type"].content.lower():
        return RunnableLambda(get_changed_orders)
    elif "주문 취소" in info["inquiry_type"].content.lower():
        return RunnableLambda(get_canceled_orders)
    else:
        return RunnableLambda(get_completed_orders)


def inquiry_request_route(info):
    from .chains import handle_inquiry_chain, handle_request_chain
    print("="*70)
    print("inquiry_request_route 함수로 전달된 데이터 -> ", info)
    if "문의" in info["msg_type"].content.lower():
        return handle_inquiry_chain
    else:
        return handle_request_chain
    

# 구버전
def requeset_types_route(info):
    from .chains import order_chain, order_cancel_chain
    print("="*70)
    print("requeset_types_route 함수로 전달된 데이터 -> ", info)
    if "주문 변경 요청" in info["request_type"].content.lower():
        return "주문 변경 요청 체인 구현 예정 중"
    elif "주문 취소 요청" in info["request_type"].content.lower():
        return order_cancel_chain | cancel_route_by_order_id
    else:
        return order_chain

# 수정 버전
def requeset_types_route(info):
    from .chains import order_chain, classify_query_chain
    print("="*70)
    print("requeset_types_route 함수로 전달된 데이터 -> ", info)
    if "주문 요청" in info["request_type"].content:
        return order_chain
    else:
        return classify_query_chain | route_by_order_id
    

# 구버전
def cancel_route_by_order_id(info):
    print("="*70)
    print("cancel_route_by_order_id 함수로 전달된 데이터 -> ", info)
    if "조회 가능" in info["recent_orders"].content:
        return RunnableLambda(cancel_order)
    else:
        return RunnableLambda(fetch_recent_orders)

# 수정 버전
def route_by_order_id(info):
    from .chains import confirmation_chain
    print("="*70)
    print("cancel_route_by_order_id 함수로 전달된 데이터 -> ", info)
    if "조회 가능" in info["recent_orders"].content:
        return confirmation_chain
    else:
        return RunnableLambda(fetch_recent_orders)
    

def change_cancel_route(info):
    from .chains import handle_order_change_chain
    print("="*70)
    print("change_cancel_route 함수로 전달된 데이터 -> ", info)
    if "주문 변경" in info["action_type"]:
        print("주문 변경 처리 방향 진입")
        return handle_order_change_chain
    elif "주문 취소" in info["action_type"]:
        return RunnableLambda(cancel_order)
    

def execution_or_message_route(info):
    from .chains import generate_confirm_message_chain
    print("="*70)
    print("execution_or_message_route 함수로 전달된 데이터 -> ", info)
    if "yes" in info["execution_confirmation"].content.lower():
        return RunnableLambda(change_cancel_route)
    else:
        return generate_confirm_message_chain