from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from .tools import tools, determine_tool_usage, create_order
from .routes import inquiry_types_route, inquiry_request_route, requeset_types_route
from .prompts import request_type_prompt, extract_order_args_prompt, order_cancel_prompt
from .parsers import create_order_parser

from dotenv import load_dotenv
load_dotenv()


model = ChatOpenAI()


store = {}
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


message_type_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 고객 입력 메시지를 아래 두 유형 중 하나로 분류하는 로봇이야.
            -상품 문의, 주문 내역 조회, 주문 변경 내역 조회, 주문 취소 내역 조회: '문의'
            -주문 요청, 주문 변경 요청, 주문 취소 요청: '요청'
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),

    ]
)

classify_message_chain = message_type_prompt | model 

classify_message_with_memory = RunnableWithMessageHistory(
    classify_message_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

classify_message_with_memory_chain = RunnablePassthrough.assign(msg_type=classify_message_with_memory)


inquiry_type_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 고객의 문의에 대응되는 주문 상태를 판단하는 로봇이야.
            사용자가 입력한 메시지를 보고 아래 주문 상태 중 하나로 분류해야 해.
            -주문 상품에 관한 문의: '주문 완료'
            -입금 완료에 관한 문의: '입금 완료'
            -주문 변경에 관한 문의: '주문 변경'
            -주문 취소에 관한 문의: '주문 취소'
            """
        ),
        ("human", "{input}"),

    ]
)

classify_inquiry_chain = RunnablePassthrough.assign(inquiry_type=inquiry_type_prompt | model)


handle_inquiry_chain = classify_inquiry_chain | RunnableLambda(inquiry_types_route)


full_chain = classify_message_with_memory_chain | inquiry_request_route


classify_request_chain = RunnablePassthrough.assign(request_type=request_type_prompt | model)


extract_order_args_chain = extract_order_args_prompt | model | create_order_parser


order_chain = extract_order_args_chain | create_order


handle_request_chain = classify_request_chain | RunnableLambda(requeset_types_route)


order_cancel_chain = RunnablePassthrough.assign(recent_orders=order_cancel_prompt | model )

#------------------------------------------------------------------------------------------
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "너는 뛰어나고 유능한 주문봇이야"
            "이전 대화와 현재 고객이 입력한 메시지 모두를 꼼꼼히 파악하여 답변해줘."
            """
            튜플의 첫 번째 값이 모델 필드에 입력된 값을 의미해
            STATUS_CHOICES = (
                ('order', '주문 완료'),
                ('payment_completed', '입금 완료'),
                ('order_changed', '주문 변경'),
                ('order_canceled', '주문 취소'),
            )"""
            "도구는 도구 호출에 필요한 추출 할 수 있을 때만 사용 가능해"
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "사용자 ID: {user_id}\n사용자 입력 메시지{input}"),
    ]
)

chain_with_tools = prompt | model.bind_tools(tools) | determine_tool_usage

chain_with_tools_n_history  = RunnableWithMessageHistory(
    chain_with_tools,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)