from langchain_openai.chat_models import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter

from .tools import tools, determine_tool_usage, create_order
from .routes import (
    inquiry_types_route, 
    inquiry_request_route, 
    requeset_types_route,
    execution_or_message_route,
)
from .prompts import (
    message_type_prompt,
    general_inquiry_prompt,
    inquiry_type_prompt,
    request_type_prompt, 
    extract_order_args_prompt, 
    classify_query_prompt,
    order_change_cancel_prompt,
    classify_confirmation_prompt,
    generate_confirm_message_prompt,
    order_change_prompt,
    )
from .parsers import create_order_parser, order_detail_parser
from .helpers import add_memory, add_action_type
from .tools import fetch_products, fetch_order_details, update_order

from dotenv import load_dotenv
load_dotenv()

SESSION_ID = "240522"
model_name = ""
model = ChatOpenAI()
specific_model = ChatOpenAI(model="gpt-4o")


# 문의 or 요청 분류 체인
classify_message_chain = message_type_prompt | model | StrOutputParser()
classify_message_with_memory = add_memory(classify_message_chain, SESSION_ID, context="classify_message_with_memory 응답", save_mode="both")
classify_message_with_memory_chain = RunnablePassthrough.assign(msg_type=classify_message_with_memory)

# 문의 담당 하위 체인
# 일반 문의
general_inquiry_chain = general_inquiry_prompt | model | StrOutputParser()
general_inquiry_chain_with_memory = add_memory(general_inquiry_chain, SESSION_ID, context="general_inquiry_chain", save_mode="output")

# 문의 유형 분류 체인
classify_inquiry_chain = inquiry_type_prompt | model | StrOutputParser()
classify_inquiry_with_memory = add_memory(classify_inquiry_chain, SESSION_ID, context="classify_inquiry_with_memory 응답", save_mode="output")
classify_inquiry_with_memory_chain = RunnablePassthrough.assign(inquiry_type=classify_inquiry_with_memory)
# 문의 담당 체인(문의 유형 분류 -> 각 문의 유형 별 처리)
handle_inquiry_chain = classify_inquiry_with_memory_chain | RunnableLambda(inquiry_types_route)

# 요청 유형 분류 체인
classify_request_chain = request_type_prompt | model | StrOutputParser()
classify_request_with_memory = add_memory(classify_request_chain, SESSION_ID, context="classify_request_with_memory 응답", save_mode="output")
classify_request_with_memory_chain = RunnablePassthrough.assign(request_type=classify_request_with_memory)
# 요청 담당 체인(요청 유형 분류 -> 각 요청 유형 별 처리)
handle_request_chain = classify_request_with_memory_chain | RunnableLambda(requeset_types_route)

# 주문 처리에 필요한 인자 추출 체인
extract_order_args_chain = RunnablePassthrough.assign(products=fetch_products) | extract_order_args_prompt | model | create_order_parser
# 주문 처리 체인
order_chain = extract_order_args_chain | create_order

# 최근 주문내역 조회 체인
# order_cancel_chain = RunnablePassthrough.assign(recent_orders=order_cancel_prompt | model )
classify_query_chain = RunnablePassthrough.assign(recent_orders=classify_query_prompt | model | StrOutputParser())

# '주문 변경' 또는 '주문 취소' 분류 체인
classify_change_or_cancel_chain = order_change_cancel_prompt | model | StrOutputParser()
classify_change_or_cancel_chain_with_memory = add_memory(classify_change_or_cancel_chain, SESSION_ID, context="classify_change_or_cancel_chain_with_memory 응답", save_mode="output")


# 사용자 승인 여부 판단 체인
classify_confirmation_chain = (RunnablePassthrough.assign(queried_result=RunnableLambda(fetch_order_details)) 
                               | classify_confirmation_prompt | model | StrOutputParser()
                               )
classify_confirmation_chain_with_memory = add_memory(classify_confirmation_chain, SESSION_ID, context="classify_confirmation_chain_with_memory  응답", save_mode="output")


# '주문 변경' 또는 '주문 취소' 진행에 대한 사용자 승인 여부 판단 체인
# itemgetter("input") 사용해 수정하기
confirmation_chain = (
    {
        "inputs": RunnablePassthrough(),
        "action_type": classify_change_or_cancel_chain_with_memory,
        # "action_type": itemgetter("action_type")
    } 
    | RunnableLambda(add_action_type) # 빼니깐 오류 발생. input, order_id 없다 등
    | RunnablePassthrough.assign(execution_confirmation=classify_confirmation_chain_with_memory)
    )


# 승인 메시지 생성 체인
# generate_confirm_message_chain = RunnablePassthrough.assign(queried_result=fetch_order_details) | generate_confirm_message_prompt | model | StrOutputParser()
generate_confirm_message_chain = RunnablePassthrough.assign(queried_result=fetch_order_details) | generate_confirm_message_prompt | model | StrOutputParser()

# 주문 변경에 필요한 인자 추출(주문 변경 내용 처리) 체인
order_change_chain = order_change_prompt | model | order_detail_parser

# handle_order_change_chain = RunnablePassthrough.assign(products=RunnableLambda(fetch_products)) | order_change_chain 

# 주문 변경 체인
handle_order_change_chain = (
    {"input": itemgetter("input"),
     "products": RunnableLambda(fetch_products), 
     "queried_result": RunnableLambda(fetch_order_details)}
     | order_change_chain
     | RunnableLambda(update_order)) 


# '주문 변경' 또는 '주문 처리' 담당 체인(종합) 
handle_change_cancel_chain = confirmation_chain | execution_or_message_route
# handle_change_cancel_chain = confirmation_chain | RunnablePassthrough.assign(confirm_message=generate_confirm_message_chain)
handle_change_cancel_chain_with_memory = add_memory(handle_change_cancel_chain, SESSION_ID, context="선택 주문 처리 결과", save_mode="both")

# 최종 체인
# full_chain = classify_message_with_memory_chain | inquiry_request_route
full_chain = classify_message_with_memory_chain | inquiry_request_route