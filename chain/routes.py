from langchain_core.runnables import RunnableLambda, RunnablePassthrough
import json

from .tools import (
    get_completed_orders, 
    get_payment_completed_orders, 
    get_changed_orders, 
    get_canceled_orders,
    fetch_recent_orders,
    create_order, 
    cancel_order,
    )

def input_route(info):
    print("="*70)
    print("input_route 함수로 전달된 데이터\n", info)
    from .chains import full_chain

    if info["request_type"]:
        # return RunnableLambda(confirm_message_route)
        return RunnableLambda(requeset_types_route)
    else: 
        return full_chain


def inquiry_types_route(info):
    from .chains import general_inquiry_chain_with_memory
    
    print("="*70)
    print("inquiry_types_route 함수로 전달된 데이터\n", info)

    if "입금 완료" in info["inquiry_type"].content:
        return RunnableLambda(get_payment_completed_orders)
    elif "주문 완료" in info["inquiry_type"].content:
        return RunnableLambda(get_completed_orders)
    elif "주문 변경" in info["inquiry_type"].content:
        return RunnableLambda(get_changed_orders)
    elif "주문 취소" in info["inquiry_type"].content:
        return RunnableLambda(get_canceled_orders)
    else:
        return general_inquiry_chain_with_memory


def inquiry_request_route(info):
    from .chains import handle_inquiry_chain, handle_request_chain
    
    print("="*70)
    print("inquiry_request_route 함수로 전달된 데이터\n", info)

    if "문의" in info["msg_type"].content:
        return handle_inquiry_chain
    else:
        return handle_request_chain
    # return handle_request_chain
    

def requeset_types_route(info):
    from .chains import handle_order_chain, classify_query_chain

    # formatted_info = json.dumps(info, indent=4, ensure_ascii=False)
    print("="*70)
    print("requeset_types_route 함수로 전달된 데이터\n", info)

    if "주문 요청" in info["request_type"].content:
        return handle_order_chain # 여기에 확인 메시지 생성, 이에 따른 라우팅 처리 포함된 체인 넣어야
    else:
        return classify_query_chain | route_by_order_id
    # return classify_query_chain | route_by_order_id


def confirm_message_route(info):
    from .chains import handle_order_chain, classify_query_chain

    print("="*70)
    print("confirm_message_route 함수로 전달된 데이터\n", info)

    if "주문 요청" in info["request_type"]:
        return handle_order_chain
    else:
        return classify_query_chain | route_by_order_id
    

def route_by_order_id(info):
    # handle_change_cancel_chain을 주문 변경 또는 취소 요청에 대한 확인 메시지 작성 체인으로 수정함
    from .chains import handle_change_cancel_chain_with_memory
    
    print("="*70)
    print("route_by_order_id 함수로 전달된 데이터\n", info)

    if "조회 불가능" in info["recent_orders"]:
        return RunnableLambda(fetch_recent_orders)
    else:
        return handle_change_cancel_chain_with_memory


def order_execution_or_message_route(info):
    from .chains import generate_order_confirmation_chain, order_chain 
    
    print("="*70)
    print("order_execution_or_message_route 함수로 전달된 데이터\n", info)
    
    if "no" in info["execution_confirmation"].content:
        return RunnablePassthrough.assign(confirm_message=generate_order_confirmation_chain)
    else:
        return order_chain # 기존 order_chain을 여기에 넣어야 할 듯

def change_cancel_route(info):
    from .chains import handle_order_change_chain

    print("="*70)
    print("change_cancel_route 함수로 전달된 데이터\n", info)
    
    if "주문 변경" in info["request_type"].content:
        return handle_order_change_chain
    elif "주문 취소" in info["request_type"].content:
        return RunnableLambda(cancel_order)
    

def execution_or_message_route(info):
    from .chains import generate_confirm_message_chain

    print("="*70)
    print("execution_or_message_route 함수로 전달된 데이터\n", info)
    
    if "no" in info["execution_confirmation"].content:
        return RunnablePassthrough.assign(confirm_message=generate_confirm_message_chain)
    else:
        return RunnableLambda(change_cancel_route)