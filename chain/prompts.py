from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from .parsers import create_order_parser


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
        ("human", "{input}"),

    ]
)


request_type_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 주문 관련 요청을 분류하는 로봇이야.
            주문 관련 요청을 다음 중 하나로 분류해야 해: '주문 요청', '주문 변경 요청', '주문 취소 요청'
            """
        ),
        ("human", "{input}"),

    ]
)


extract_order_args_prompt = PromptTemplate(
    template="""
    You are a robot designed to extract necessary parameters for processing each order request.
    Only include the extracted parameters in your response.

    Product Information:
    {products}

    User ID: {user_id}

    User Input: {input}

    Provide only the extracted parameters in the following format:
    {format_instructions}
    """,
    input_variables=["user_id", "input", "products"],
    partial_variables={"format_instructions": [create_order_parser.get_format_instructions()]},
)


order_cancel_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that determines whether the customer input message contains an order_id.
            If the input contains an order_id, respond with '조회 가능'.
            If the input does not contain an order_id, respond with '조회 불가능'.
            """
        ),
        ("human", "input: {input}\norder_id: {order_id}")
    ]
)