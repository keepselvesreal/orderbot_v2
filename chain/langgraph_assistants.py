from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from django.db.models import QuerySet

from .files.product_list import product_list
from .langgraph_states import State
from .langgraph_tools import (
    lookup_policy, fetch_product_list,
    fetch_recent_order, fetch_change_order, fetch_cancel_order, 
    create_order, change_order, cancel_order,
    # GPT는 아래 pydantic model을 user_request.py로 빼는 걸 추천
    CompleteOrEscalate, ToOrderAssistant, ToOrderInquiryAssistant, ToOrderUpdateAssistant
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


order_create_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 조건에 따라 정해진 응답을 생성해야 해.
            각 조건과 이 조건에서 생성해야 하는 응답은 아래와 같아.
            - Product Presentation이 False인 경우: "present_product_list"
            - Product Presentation이 True이고 user_approval이 False인 경우: "request_approval"
            - Product Presentation이 user_approval이 True인 경우: "use_create_tool"  

            응답 전에 각 조건에 대응되는 응답인지 확실하게 확인하고 응답해줘.
            응답은 반드시 "present_product_list", "request_approval", "use_create_tool" 중 하나여야만 해.


            Current user ID: {user_info}
            Product Presentation: {product_presentation}.
            User Approval: {user_approval}.
            Current time: {time}.
            """,
        ),
        # MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

llm = ChatOpenAI()
order_create_runnable = order_create_prompt | llm


present_product_list_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 사용자에게 판매 중인 상품 정보를 보여주는 주문봇이야.
        
        만약 사용자가 구체적으로 언급한 상품 정보가 있다면 아래 내용을 반영해 응답 메시지를 작성해줘.
        -사용자가 언급한 상품 정보가 판매 중인 상품 정보와 다르다면, 
         가장 유사한 상품 정보를 찾아 사용자가 말하는 상품이 해당 상품이 맞는지 확인.
        -판매 중인 상품을 보여주며, 추가로 주문하길 원하는 상품이 있는지 물어보며 구매 유도.
        
        만약 사용자가 구체적으로 언급한 상품 정보가 없다면, 판매 중인 상품을 알려주고 그 가운데 주문을 원하는 상품을 알려달라고 요청해.

        판매 중인 상품
        {product_list}
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
)
llm =  ChatOpenAI()
present_product_list_runnable = present_product_list_prompt | llm


use_create_tool_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 사용자 요청대로 새로운 주문을 하는 주문봇이야.
        User ID와 사용자의 요청을 꼼꼼히 확인하여 도구 사용에 필요한 인자를 정확하게 추출해줘.
        주문 상세내역을 작성 시 판매 상품 목록의 정보와 비교하여 반드시 정확한 정보를 기입해야 해. 

        Current user ID: {user_info}
        Product_list: {product_list}

        Please provide the order details in the following format:
              items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
              'product_name': The name of the product (str)
              'quantity': The quantity of the product (int)
              'price': The price of the product (float)
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(product_list=product_list)
llm =  ChatOpenAI()
create_tool = [create_order]
use_create_tool_runnable = use_create_tool_prompt | llm.bind_tools(create_tool)


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

order_update_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 조건에 따라 정해진 응답을 생성해야 해.
            각 조건과 이 조건에서 생성해야 하는 응답은 아래와 같아.
            - order_id가 주어지지 않은 경우: "display_user_order"
            - order_id가 주어지고 user_approval이 False인 경우: "request_approval"
            - order_id가 주어지고 user_approval이 True인 경우: "use_update_tools"  

            응답 전에 각 조건에 대응되는 응답인지 확실하게 확인하고 응답해줘.
            응답은 반드시 "display_user_order", "request_approval", "use_update_tools" 중 하나여야만 해.


            Current user ID: {user_info}
            Order ID: {order_id}.
            User Approval: {user_approval}.
            Current time: {time}.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

llm = ChatOpenAI()
order_update_runnable = order_update_prompt | llm


ask_order_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        "너는 사용자에게 변경할 주문을 묻는 주문봇이야"
        "너가 반환하는 응답에는 아래 내용이 포함돼야 해."
        "사용자의 주문 내역"
        "사용자가 변경을 원하는 주문 내역"
        "사용자가 원하는 주문 변경 내역"
        "사용자 주문 내역: {orders}"),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
)
llm =  ChatOpenAI()
ask_order_runnable = ask_order_prompt | llm 


request_approval_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 사용자의 요청한 작업을 수행하기 전 최종 승인 여부를 확인하는 주문봇이야.
        사용자가 선택한 기존 주문 내역과 사용자가 현재 요청한 작업을 각각 제시하여 사용자가 선택한 주문과 요청한 작업을 분명하게 확인하도록 해줘.
        요청 작업 수행을 사용자가 승인하는지 물어보는 메시지를 작성해줘.

        주의! 사용자가 입력한 상품명, 가격 등이 아래 상품 목록의 정보와 다른 경우 대처법
        - 사용자가 입력한 내용을 상품 목록 가운데 사용자가 입력한 내용과 가장 유사한 상품으로 변경하여 메시지를 작성해줘.

        사용자 선택한 기존 주문 내역: {orders}
        판매 중인 상품 목록
        {product_list}
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
)
llm =  ChatOpenAI()
request_approval_runnable = request_approval_prompt | llm 


use_update_tool_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        "너는 주문 변경 또는 주문 취소를 처리하는 주문봇이야"
        "사용자의 요청을 꼼꼼히 확인한 후에 적절한 도구를 사용해줘"
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
llm =  ChatOpenAI()
update_tools = [change_order, cancel_order]
use_update_tool_runnable = use_update_tool_prompt | llm.bind_tools(update_tools)


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
        ToOrderUpdateAssistant,
        ToOrderAssistant,
        ]
    )