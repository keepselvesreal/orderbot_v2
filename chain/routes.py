from langchain_core.runnables import RunnableLambda

from .tools import get_completed_orders, get_payment_completed_orders, get_changed_orders, get_canceled_orders


def inquiry_types_route(info):
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
    print("inquiry_request_route 함수로 전달된 데이터 -> ", info)
    if "문의" in info["msg_type"].content.lower():
        return handle_inquiry_chain
    else:
        return handle_request_chain
    

def requeset_types_route(info):
    from .chains import order_chain
    print("requeset_types_route 함수로 전달된 데이터 -> ", info)
    if "주문 변경 요청" in info["request_type"].content.lower():
        return "주문 변경 요청 체인 구현 예정 중"
    elif "주문 취소 요청" in info["request_type"].content.lower():
        return "주문 변경 요청 체인 구현 예정 중"
    else:
        return order_chain