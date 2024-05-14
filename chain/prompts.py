from langchain_core.prompts import ChatPromptTemplate

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