from langchain_core.runnables import RunnableLambda, RunnablePassthrough
import json

from .tools import (
    get_completed_orders, 
    get_payment_completed_orders, 
    get_changed_orders, 
    get_canceled_orders,
    fetch_recent_orders, 
    cancel_order,
    )


def inquiry_types_route(info):
    from .chains import general_inquiry_chain_with_memory
    
    print("="*70)
    print("inquiry_types_route 함수로 전달된 데이\n", info)

    if "입금 완료" in info["inquiry_type"]:
        return RunnableLambda(get_payment_completed_orders)
    elif "주문 완료" in info["inquiry_type"]:
        return RunnableLambda(get_completed_orders)
    elif "주문 변경" in info["inquiry_type"]:
        return RunnableLambda(get_changed_orders)
    elif "주문 취소" in info["inquiry_type"]:
        return RunnableLambda(get_canceled_orders)
    else:
        return general_inquiry_chain_with_memory


def inquiry_request_route(info):
    from .chains import handle_inquiry_chain, handle_request_chain
    
    print("="*70)
    print("inquiry_request_route 함수로 전달된 데이터\n", info)

    # if "문의" in info["msg_type"]:
    #     return handle_inquiry_chain
    # else:
    #     return handle_request_chain
    return handle_request_chain
    

def requeset_types_route(info):
    from .chains import order_chain, classify_query_chain

    # formatted_info = json.dumps(info, indent=4, ensure_ascii=False)
    print("="*70)
    print("requeset_types_route 함수로 전달된 데이터\n", info)
    # if "주문 요청" in info["request_type"]:
    #     return order_chain
    # else:
    #     return classify_query_chain | route_by_order_id
    return classify_query_chain | route_by_order_id
    

def route_by_order_id(info):
    # handle_change_cancel_chain을 주문 변경 또는 취소 요청에 대한 확인 메시지 작성 체인으로 수정함
    from .chains import handle_change_cancel_chain, handle_change_cancel_chain_with_memory
    
    print("="*70)
    print("route_by_order_id 함수로 전달된 데이터\n", info)

    if "조회 가능" in info["recent_orders"]:
        # return handle_change_cancel_chain
        return handle_change_cancel_chain_with_memory
        # return handle_change_cancel_chain
    else:
        return RunnableLambda(fetch_recent_orders)
    

def change_cancel_route(info):
    from .chains import handle_order_change_chain

    print("="*70)
    print("change_cancel_route 함수로 전달된 데이터\n", info)
    
    if "주문 변경" in info["action_type"]:
        return handle_order_change_chain
    elif "주문 취소" in info["action_type"]:
        return RunnableLambda(cancel_order)
    

def execution_or_message_route(info):
    from .chains import generate_confirm_message_chain
    
    print("="*70)
    print("execution_or_message_route 함수로 전달된 데이터\n", info)
    
    if "yes" in info["execution_confirmation"]:
        return RunnableLambda(change_cancel_route)
    else:
        return RunnablePassthrough.assign(confirm_message=generate_confirm_message_chain)