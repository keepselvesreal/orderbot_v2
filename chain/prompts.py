from langchain_core.prompts import (
    ChatPromptTemplate, 
    PromptTemplate, 
    MessagesPlaceholder
)
import os
import json

from .parsers import request_type_parser, create_order_parser, order_detail_parser



base_dir = os.path.dirname(__file__)
# products.json 파일의 절대 경로를 구합니다
file_path = os.path.join(base_dir, 'files', 'products.json')

with open(file_path, 'r', encoding='utf-8') as file:
    products = json.load(file)


route_input_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """

            """
        ),
        ("human", "{request_type}\n{input}"),
    ]
)

message_type_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that classifies customer input messages into one of the following two types:
            - Product inquiry, order history inquiry, order change history inquiry, order cancellation history inquiry: '문의'
            - Order request, order change request, order cancellation request: '요청'
            
            '문의' refers to messages where the customer is seeking information or asking about details, such as product information or past orders.
            '요청' refers to messages where the customer wants to perform an action, such as placing a new order, changing an existing order, or cancelling an order.
            
            You need to review the messages in the Messages Placeholder from the latest to the oldest to understand the context. 
            However, your response should be based solely on the current input and should only be one of the required response types: '문의' or '요청'.
            
            If the latest AI response was classified as '요청', and the current input is related to an order, it is likely a '요청'.
            
            Ensure your classification fits one of the specified categories. If it does not, choose the most appropriate category and output the classification.

            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)


general_inquiry_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a customer service assistant. 
            Your role is to help customers with their inquiries that are not related to orders. This includes questions about products, services, store policies, and other general information. 
            Be polite, informative, and efficient in your responses.
            
            The products on sale are listed below:
            {products}
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
).partial(products=products) 


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
            - General inquiries about products or other matters: '일반 문의'
            
            You need to review the messages in the Messages Placeholder from the latest to the oldest.
            Pay particular attention to the latest HumanMessage when making the classification.

            Ensure your classification fits one of the specified categories. If it does not, choose the most appropriate category and output the classification.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)

request_type_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that classifies order-related requests.
            You need to classify the order-related request into one of the following types: '주문 요청', '주문 변경 요청', '주문 취소 요청'
            You need to review the messages in the Messages Placeholder from the latest to the oldest.
            
            If any previous AI response in the Messages Placeholder was classified as '주문 변경 요청' or '주문 취소 요청', consider this context and classify the current input accordingly.
            
            Ensure your classification fits one of the specified categories. If it does not, choose the most appropriate category and output the classification.

            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)


# using parser case
# request_type_prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             """
#             You are a robot that classifies order-related requests.
#             You need to classify the order-related request into one of the following types: '주문 요청', '주문 변경 요청', '주문 취소 요청'
#             You need to review the messages in the Messages Placeholder from the latest to the oldest.
            
#             If any previous AI response in the Messages Placeholder was classified as '주문 변경 요청' or '주문 취소 요청', consider this context and classify the current input accordingly.
#             Wrap the output in `json` tags\n{format_instructions}"
#             """
#         ),
#         MessagesPlaceholder(variable_name="chat_history"),
#         ("human", "{input}"),
#     ]
# ).partial(format_instructions=request_type_parser.get_format_instructions())


extract_order_args_prompt = PromptTemplate(
    template="""
    You are a robot designed to extract necessary parameters for processing each order request.
    Only include the extracted parameters in your response.

    Product Information:
    {products}

    User ID: {user_id}

    confirm_message: {confirm_message}

    Provide only the extracted parameters in the following format:
    {format_instructions}
    """,
    input_variables=["user_id", "confirm_message", "products"],
    partial_variables={"format_instructions": [create_order_parser.get_format_instructions()]},
)


generate_order_confirmation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an assistant responsible for generating order confirmation messages. 
            Your task is to create a clear and concise order confirmation message in Korean based on the provided list of products and the user's input. 
            Ensure that the message includes all necessary details such as product names, quantities, prices, and any other relevant information from the user input.
            Summarize the order details and ask the user to confirm if they would like to proceed with the order.
             """
        ),
        ("human", "products:{request_type}\ninput:{input}")
    ]
)


classify_query_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that determines whether the customer input message contains an order_id.
            If the input contains an order_id, respond with '조회 가능'.
            If the input does not contain an order_id, respond with '조회 불가능'.

            Ensure your classification fits one of the specified categories. If it does not, choose the most appropriate category and output the classification.
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

            Ensure your classification fits one of the specified categories. If it does not, choose the most appropriate category and output the classification.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "input:{input}\norder_id:{order_id}"),
    ]
)


order_change_prompt = PromptTemplate(
    template="""
    You are a customer service assistant responsible for processing order changes based on customer input and existing order details.
    
    Given the 'queried_result' which contains existing order details and the 'input' which contains the customer's desired order changes, combine these to finalize the order changes.
    
    Follow these steps:
    1. Review the 'queried_result' to understand the original order details.
    2. Review the 'input' to understand the customer's desired changes.
    3. Combine both sets of information to produce the updated order details, ensuring that the quantity of each item is greater than 0. Do not include items with a quantity of 0.
    
    Ensure that the final output includes only the updated items in the order, formatted the same way as the original order, and set the order_status to '주문 변경'.

    {format_instructions}
    products: {products}
    queried_result: {queried_result}
    input: {input}
    """,
    input_variables=["products", "queried_result", "input"],
    partial_variables={"format_instructions": order_detail_parser.get_format_instructions()},
)


generate_confirm_message_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that generates a confirmation request message based on the request_type and queried_result.
            Create a message to show the queried_result and ask for final confirmation considering request_type.
            The response should be generated in Korean.
            Make sure to clarify that the queried_result is the order detail the user wants to place, change or cancel, and this is for final confirmation.
            Based on the request_type, ask the user if they want to proceed with the specified action.
            """
        ),
        ("human", "request_type:{request_type}\nqueried_result:{queried_result}")
    ]
)


classify_confirmation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a robot that classifies customer input messages into specific types. 
            You need to determine whether the user has responded to the AI's request for approval regarding the action specified in request_type.
            
            To make this determination, you should use the following information:
            1. The variable 'confirm_message' contains the AI's message asking for approval for the action specified in request_type, based on the specified order details.
            2. The variable 'input' contains the user's response to this request.

            If 'confirm_message' contains the AI's request and 'input' indicates agreement or action, you should respond with 'yes'. 
            Otherwise, you should respond with 'no'.
            
            Your response must be either 'yes' or 'no'.
            Ensure your classification fits one of the specified categories. If it does not, choose the most appropriate category and output the classification.

            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "request_type: {request_type}\nconfirm_message: {confirm_message}\ninput:{input}"),
    ]
)





