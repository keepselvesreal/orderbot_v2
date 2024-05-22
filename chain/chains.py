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


classify_message_chain = message_type_prompt | model | StrOutputParser()

classify_message_with_memory = add_memory(classify_message_chain, SESSION_ID, context="classify_message_with_memory 응답", save_mode="both")

classify_message_with_memory_chain = RunnablePassthrough.assign(msg_type=classify_message_with_memory)

general_inquiry_chain = general_inquiry_prompt | model

general_inquiry_chain_with_memory = add_memory(general_inquiry_chain, SESSION_ID, context="general_inquiry_chain", save_mode="both")

classify_inquiry_chain = inquiry_type_prompt | model

classify_inquiry_with_memory = add_memory(classify_inquiry_chain, SESSION_ID, context="classify_inquiry_with_memory 응답", save_mode="output")

classify_inquiry_with_memory_chain = RunnablePassthrough.assign(inquiry_type=classify_inquiry_with_memory)

handle_inquiry_chain = classify_inquiry_with_memory_chain | RunnableLambda(inquiry_types_route)


classify_request_chain = request_type_prompt | model

classify_request_with_memory = add_memory(classify_request_chain, SESSION_ID, context="classify_request_with_memory 응답", save_mode="output")

classify_request_with_memory_chain = RunnablePassthrough.assign(request_type=classify_request_with_memory)

handle_request_chain = classify_request_with_memory_chain | RunnableLambda(requeset_types_route)


extract_order_args_chain = RunnablePassthrough.assign(products=fetch_products) | extract_order_args_prompt | model | create_order_parser

order_chain = extract_order_args_chain | create_order


# order_cancel_chain = RunnablePassthrough.assign(recent_orders=order_cancel_prompt | model )
classify_query_chain = RunnablePassthrough.assign(recent_orders=classify_query_prompt | model )

# 메모리 필요
classify_change_or_cancel_chain = order_change_cancel_prompt | model

classify_change_or_cancel_chain_with_memory = add_memory(classify_change_or_cancel_chain, SESSION_ID, context="classify_change_or_cancel_chain_with_memory 응답", save_mode="output")


# 메모리 필요
classify_confirmation_chain = classify_confirmation_prompt | model

classify_confirmation_chain_with_memory = add_memory(classify_confirmation_chain, SESSION_ID, context="classify_confirmation_chain_with_memory  응답", save_mode="output")


confirmation_chain = (
    {
        "inputs": RunnablePassthrough(),
        "action_type": classify_change_or_cancel_chain_with_memory
    } 
    | RunnableLambda(add_action_type) 
    | RunnablePassthrough.assign(execution_confirmation=classify_confirmation_chain_with_memory)
    )


generate_confirm_message_chain = RunnablePassthrough.assign(queried_result=fetch_order_details) | generate_confirm_message_prompt | model 


order_change_chain = order_change_prompt | model | order_detail_parser

# handle_order_change_chain = RunnablePassthrough.assign(products=RunnableLambda(fetch_products)) | order_change_chain 

handle_order_change_chain = (
    {"input": itemgetter("input"),
     "products": RunnableLambda(fetch_products), 
     "queried_result": RunnableLambda(fetch_order_details)}
     | order_change_chain
     | RunnableLambda(update_order)) 


# 종합 체인
# handle_change_cancel_chain = confirmation_chain | execution_or_message_route
handle_change_cancel_chain = confirmation_chain | RunnablePassthrough.assign(confirm_message=generate_confirm_message_chain)

handle_change_cancel_chain_with_memory = add_memory(handle_change_cancel_chain, SESSION_ID, context="선택 주문 처리 결과", save_mode="both")

# full_chain = classify_message_with_memory_chain | inquiry_request_route

full_chain = classify_message_with_memory_chain
#------------------------------------------------------------------------------------------
# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             "너는 뛰어나고 유능한 주문봇이야"
#             "이전 대화와 현재 고객이 입력한 메시지 모두를 꼼꼼히 파악하여 답변해줘."
#             """
#             튜플의 첫 번째 값이 모델 필드에 입력된 값을 의미해
#             STATUS_CHOICES = (
#                 ('order', '주문 완료'),
#                 ('payment_completed', '입금 완료'),
#                 ('order_changed', '주문 변경'),
#                 ('order_canceled', '주문 취소'),
#             )"""
#             "도구는 도구 호출에 필요한 추출 할 수 있을 때만 사용 가능해"
#         ),
#         MessagesPlaceholder(variable_name="chat_history"),
#         ("human", "사용자 ID: {user_id}\n사용자 입력 메시지{input}"),
#     ]
# )

# chain_with_tools = prompt | model.bind_tools(tools) | determine_tool_usage

# chain_with_tools_n_history  = RunnableWithMessageHistory(
#     chain_with_tools,
#     get_session_history,
#     input_messages_key="input",
#     history_messages_key="chat_history",
# )