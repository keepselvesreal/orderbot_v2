from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from django.db.models import QuerySet

from .langgraph_states import State
from .langgraph_tools import (
    lookup_policy, fetch_product_list,
    fetch_recent_order, fetch_change_order, fetch_cancel_order, 
    create_order, change_order, cancel_order,
    # GPT는 아래 pydantic model을 user_request.py로 빼는 걸 추천
    CompleteOrEscalate, ToOrderInquiryAssistant, ToOrderRequestAssistant,
    )
from products.models import Order


model="gpt-3.5-turbo"
# model="gpt-4o"
# model="gpt-4-turbo-2024-04-09"
llm = ChatOpenAI(model=model)
llm


class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            result = self.runnable.invoke(state)

            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break

        if isinstance(result, Order):
            result = result.to_dict()
            result = AIMessage(content=result)
            # result = json.dumps(result)
        elif isinstance(result, QuerySet):
            result = [order.to_dict() for order in result]
            result = AIMessage(content=result)
        # print("assistant 출력\n", type(result))
        return {"messages": result}
    

# order inquiry assistant
order_inquiry_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a specialized assistant for handling order queries. "
            "The primary assistant delegates work to you whenever the user needs help with their orders. "
            "Confirm the order details with the customer and inform them of any additional information. "
            "If you need more information or the customer changes their mind, escalate the task back to the main assistant."
            "\n\nCurrent user ID: {user_info}"
            "\nCurrent time: {time}."
            "\n\nIf the user needs help, and none of your tools are appropriate for it, then"
            '"CompleteOrEscalate" the dialog to the host assistant. Do not waste the user\'s time. Do not make up invalid tools or functions.'
            "Do not make up or fabricate any details. Respond honestly if you lack the necessary information to address the user's query.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

inquiry_tools = [fetch_recent_order, fetch_change_order, fetch_cancel_order]
order_inquiry_runnable = order_inquiry_prompt | llm.bind_tools(   
    inquiry_tools + [CompleteOrEscalate]
)
order_inquiry_runnable

# order request assistant
order_request_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a specialized assistant for handling order queries.
            The primary assistant delegates work to you whenever the user needs help with their orders.
            Perform the order placement, modification, or cancellation as requested by the customer and inform them of any additional information or fees.
            If you need more information or the customer changes their mind, escalate the task back to the main assistant.

            Current user ID: {user_info}

            Current time: {time}.

            If the user needs help, and none of your tools are appropriate for it, then
            'CompleteOrEscalate' the dialog to the host assistant. Do not waste the user's time. Do not make up invalid tools or functions.

            Please provide the order details in the following format:
              items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
              'product_name': The name of the product (str)
              'quantity': The quantity of the product (int)
              'price': The price of the product (float)
            The product information for the items currently on sale is as follows:
            
            'product_name': "떡케익5호"
            'quantity': 1
            'price': 54000
        
            'product_name': "무지개 백설기 케익"
            'quantity': 1
            'price': 51500
        
            'product_name': "미니 백설기"
            'quantity': 35,
        
            'product_name': "개별 모듬팩"
            'quantity': 1
            'price': 13500
            """
       ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

request_tools = [create_order, change_order, cancel_order]
order_request_runnable = order_request_prompt | llm.bind_tools(   
    request_tools + [CompleteOrEscalate]
)
order_request_runnable


primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful customer support assistant "
            "Your primary role is to search for company policies to answer customer queries. "
            "If a customer requests order-related inquiries (such as checking past orders, viewing order changes, or viewing order cancellations)"
            "or order-related requests (such as placing an order, changing an order, or canceling an order), delegate the task to the appropriate specialized assistant."
            "Only the specialized assistants are given permission to do this for the user."
            "The user is not aware of the different specialized assistants, so do not mention them; just quietly delegate through function calls. "
            "\n\nCurrent user:\n<User>\n{user_info}\n</User>"
            "\nCurrent time: {time}.",
        ),
        # ("placeholder", "{messages}"),
        MessagesPlaceholder(variable_name="messages")
    ]
).partial(time=datetime.now())

primary_assistant_tools = [
    lookup_policy,
    fetch_product_list,
]
primary_assistant_runnable = primary_assistant_prompt | llm.bind_tools(
    primary_assistant_tools
    + [
        ToOrderInquiryAssistant,
        ToOrderRequestAssistant,
        ]
    )