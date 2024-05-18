from langchain_core.prompts import (
    ChatPromptTemplate, 
    PromptTemplate, 
    MessagesPlaceholder
)

from .parsers import create_order_parser, order_detail_parser


# message_type_prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             """
#             You are a robot that classifies customer input messages into one of the following two types:
#             - Product inquiry, order history inquiry, order change history inquiry, order cancellation history inquiry: '문의'
#             - Order request, order change request, order cancellation request: '요청'
#             You need to review the messages in the Messages Placeholder from the latest to the oldest.
#             Pay particular attention to the latest HumanMessage when making the classification.
#             """
#         ),
#         MessagesPlaceholder(variable_name="chat_history"),
#         ("human", "{input}"),

#     ]
# )
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

message_type_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that classifies customer input messages into one of the following two types:
            - Product inquiry, order history inquiry, order change history inquiry, order cancellation history inquiry: '문의'
            - Order request, order change request, order cancellation request: '요청'
            
            You need to review the messages in the Messages Placeholder from the latest to the oldest.

            Consider the previous AI responses and their classifications to understand the intent behind the current input. 
            Use this context to make an accurate classification. 
            If the latest AI response was classified as '요청', and the current input is related to an order, it is likely a '요청'.
            
            Additionally, if the input contains order details, it should be classified as '요청'.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)


# inquiry_type_prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             """
#             너는 고객의 문의에 대응되는 주문 상태를 판단하는 로봇이야.
#             사용자가 입력한 메시지를 보고 아래 주문 상태 중 하나로 분류해야 해.
#             -주문 상품에 관한 문의: '주문 완료'
#             -입금 완료에 관한 문의: '입금 완료'
#             -주문 변경에 관한 문의: '주문 변경'
#             -주문 취소에 관한 문의: '주문 취소'
#             """
#         ),
#         ("human", "{input}"),

#     ]
# )
inquiry_type_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that determines the order status corresponding to customer inquiries.
            Based on the user's input message, you need to classify it into one of the following order statuses:
            - Inquiry about ordered products: '주문 완료'
            - Inquiry about payment completion: '입금 완료'
            - Inquiry about order changes: '주문 변경'
            - Inquiry about order cancellations: '주문 취소'
            You need to review the messages in the Messages Placeholder from the latest to the oldest.
            Pay particular attention to the latest HumanMessage when making the classification.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)



# request_type_prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             """
#             너는 주문 관련 요청을 분류하는 로봇이야.
#             주문 관련 요청을 다음 중 하나로 분류해야 해: '주문 요청', '주문 변경 요청', '주문 취소 요청'
#             """
#         ),
#         ("human", "{input}"),

#     ]
# )
request_type_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that classifies order-related requests.
            You need to classify the order-related request into one of the following types: '주문 요청', '주문 변경 요청', '주문 취소 요청'
            You need to review the messages in the Messages Placeholder from the latest to the oldest.
            
            If any previous AI response in the Messages Placeholder was classified as '주문 변경 요청' or '주문 취소 요청', consider this context and classify the current input accordingly.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
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


classify_query_prompt = ChatPromptTemplate.from_messages(
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


order_change_cancel_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that classifies customer input messages into specific types. 
            You need to review the messages in the Messages Placeholder from the latest to the oldest and output either '주문 변경' or '주문 취소'.
            Pay particular attention to the latest HumanMessage when making the classification.
            Ensure to focus on specific keywords for classification:
            - If the message contains words like '취소', '취소하고 싶어', '취소해주세요', classify it as '주문 취소'.
            - If the message contains words like '변경', '바꾸고 싶어', '변경해주세요', classify it as '주문 변경'.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "input:{input}\norder_id:{order_id}"),
    ]
)


classify_confirmation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that classifies customer input messages into specific types. 
            You need to determine whether the user has responded to the AI's request for approval regarding the action specified in action_type.
            
            To make this determination, the following conditions must be met:
            1. There must be an AIMessage that asks for approval for the action specified in action_type, based on the specified order details.
            2. The user must have explicitly expressed consent (e.g., "Yes, I approve" or "Okay, proceed with the change") in response to the AIMessage asking for approval of the action specified in action_type.
            
            The chat history is provided as a list, where the most recent message is at the end of the list. You should start checking from the most recent message and move backwards.

            Your response must be either 'yes' or 'no'.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "input:{input}\norder_id:{order_id}\naction_type: {action_type}"),
    ]
)


generate_confirm_message_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that generates a confirmation request message based on the action_type and queried_result.
            Create a message to show the queried_result and ask for final confirmation considering action_type.
            The response should be generated in Korean.
            Make sure to clarify that the queried_result is the order detail the user wants to change or cancel, and this is for final confirmation.
            Based on the action_type, ask the user if they want to proceed with the specified action.
            """
        ),
        ("human", "action_type:{action_type}\nqueried_result:{queried_result}")
    ]
)


order_change_prompt = PromptTemplate(
    template="""
    You are a customer service assistant responsible for processing order changes based on customer input and existing order details.
    
    Given the 'queried_result' which contains existing order details and the 'input' which contains the customer's desired order changes, combine these to finalize the order changes.
    
    Follow these steps:
    1. Review the 'queried_result' to understand the original order details.
    2. Review the 'input' to understand the customer's desired changes.
    3. Combine both sets of information to produce the updated order details.
    
    Ensure that the final output includes only the updated items in the order, formatted the same way as the original order, and set the order_status to '주문 변경'.

    {format_instructions}
    products: {products}
    queried_result: {queried_result}
    input: {input}
    """,
    input_variables=["products", "queried_result", "input"],
    partial_variables={"format_instructions": order_detail_parser.get_format_instructions()},
)


