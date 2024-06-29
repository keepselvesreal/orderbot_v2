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
    CompleteOrEscalate, 
    ToOrderAssistant, ToOrderChangeAssistant, ToOrderCancelAssistant,
    ToOrderInquiryAssistant,
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
                state = {"messages": messages}
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
        
        add_state = {k: v for k, v in state.items() if k != "dialog_state"}
        
        return {**add_state, "messages": result}


order_create_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 아래 조건에 따라 정해진 응답을 생성해야 해.
            각 조건과 이 조건에서 생성해야 하는 응답은 아래와 같아.
            - Product Presentation이 주어지지 않은 경우: present_product_list
            - Product Presentation이 True이고 Request Approval Message가 주어지지 않은 경우: request_approval
            - Product Presentation이 Request Approval Message가 True인 경우: use_order_create_tool

            응답 전에 각 조건에 대응되는 응답인지 확실하게 확인하고 응답해줘.
            응답은 반드시 present_product_list, request_approval, use_order_create_tool 중 하나여야만 해.


            Current user ID: {user_info}
            Product Presentation: {product_presentation}.
            Request Approval Message: {request_approval_message}.
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
        아래 단계에 따라 한글로 답변을 생성해.
        1. 판매 중인 상품 목록 제시하기.
        2. 사용자가 구체적인 상품을 언급했는지, 언급하지 않았는지 파악하기.
        3. 만약 사용자가 구체적인 상품을 언급했다면, 추가로 주문하길 원하는 상품이 있는지 물어보기.
        4. 사용자가 언급한 상품이 판매 중인 상품 목록의 상품명과 다르다면, 
           가장 유사한 상품 정보를 찾아 사용자가 말하는 상품이 해당 상품이 맞는지 확인하는 메시지 추가하기.
        5. 만약 사용자가 구체적인 상품을 언급하지 않았다면, 판매 중인 상품을 알려주고 그 가운데 주문을 원하는 상품을 알려달라고 요청하기.
        반드시 판매 중인 상품 목록은 제시되어야 해.     

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
        도구 사용에 필요한 User ID와 사용자의 주문 내역을를 정확하게 파악해야 해..
        사용자의 주문 내역은 지금까지의 Messges에서 확인할 수 있어.
        주문 상세내역을 작성 시 판매 상품 목록의 정보와 비교하여 반드시 정확한 정보를 기입해야 해. 
        Please provide the order details in the following format:
              items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
              'product_name': The name of the product (str)
              'quantity': The quantity of the product (int)
              'price': The price of the product (float)

        Current user ID: {user_info}
        Product_list: {product_list}
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(product_list=product_list)
llm =  ChatOpenAI()
order_create_tool = [create_order]
use_create_tool_runnable = use_create_tool_prompt | llm.bind_tools(order_create_tool)


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

order_change_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 아래 조건에 따라 정해진 응답을 생성해야 해.
            메시지 내용이 응답 생성에 영향을 미쳐서는 안돼. 조건에 따라서만 응답을 생성해야 해.
            - order_id가 주어지지 않은 경우: step1
            - order_id가 주어지고 request_order_change_message가 주어지지 않은 경우: step2
            - order_id가 주어지고 request_order_change_message이 True인 경우: step3
            - order_id가 주어지고 request_order_change_message이 True이며 request_approval_message가 True인 경우: step4

            응답 전에 조건을 충족하는 응답인지 확실히 확인해줘.
            응답은 반드시 step1, step2, step3, step4 중 하나여야만 해. 
            절대 다른 응답을 생성하면 안돼.

            user_id: {user_info}
            order_id: {order_id}.
            request_order_change_message: {request_order_change_message}
            request_approval_message: {request_approval_message}.
            current time: {time}.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

llm = ChatOpenAI()
order_change_runnable = order_change_prompt | llm


order_cancel_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 아래 조건에 따라 정해진 응답을 생성해야 해.
            - Order ID가 주어지지 않은 경우: step1
            - Order ID가 주어지고 Request Approval Message가 주어지지 않은 경우: step2
            - Order ID가 주어지고 Request Approval Message이 True인 경우: step3

            응답 전에 각 조건에 대응되는 응답인지 확실하게 확인하고 응답해줘.
            응답은 반드시 step1, step2, step3 중 하나여야만 해. 
            절대 다른 응답을 생성하면 안돼.


            Current user ID: {user_info}
            Order ID: {order_id}.
            Request Approval Message: {request_approval_message}.
            Current time: {time}.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

llm = ChatOpenAI()
order_cancel_runnable = order_cancel_prompt | llm


ask_order_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """
         너는 사용자에게 변경할 주문을 묻는 주문봇이야.
         너의 응답은 아래 내용을 포함해야 해.
         - 사용자의 지난 주문 내역(주문 날짜, 주문 ID, 상품명, 수량, 가격을 모두 표시하기)
         - 사용자가 변경을 원하는 주문 내역을 선택해달라는 메시지
         
         사용자 지난 주문 내역
         {orders}
         """
         ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
llm =  ChatOpenAI()
ask_order_runnable = ask_order_prompt | llm 



ask_order_change_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """
         너는 사용자에게 주문을 어떻게 변경할지 묻는 주문봇이야.
         아래 단계에 따라 답변을 생성해.
         1. 사용자가 선택한 주문 내역을 파악해. 주문 내역에는 주문 날짜, 주문 ID, 상품명, 수량, 가격이 모두 포함되어야 해.
         2. 주문을 어떻게 변경할지 알려달라는 메시지를 작성해. 이 메시지에는 위에서 파악한 주문 내역이 반드시 포함되어야 해.
         
         변경을 요청한 주문 내역
         {selected_order}
         """
         ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
)
llm =  ChatOpenAI()
ask_order_change_runnable = ask_order_change_prompt | llm 


request_approval_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 수행할 작업 내용을 확인하는 주문봇이야.
        아래 단계에 따라 답변을 생성해.
        아래 단계를 따르지 않은 답변은 절대로 생성해선 안돼.
        너는 작업을 실제로 수행할 수는 없으니 사용자가 요청한 작업을 수행했다는 종류의 내용을 답변에 포함해서는 안돼.
        1. 지금까지의 메시지를 꼼꼼히 살펴보고 사용자가 요청한 작업을 파악해.
        2. 너가 파악한 사용자 요청이 맞는지 확인하는 메시지를 작성해. 정확한 상품명, 가격, 수량이 반드시 포함돼야 해.
        3. 사용자가 요청한 작업이 주문 변경 또는 주문 취소인 경우 사용자가 선택한 주문 내역을 파악해.
        4. 지금까지 수행한 위의 작업들을 바탕으로 최종 메시지를 작성해.

        사용자의 입력이 상품 목록의 정보와 다른 경우, 상품 목록 가운데 사용자 입력과 가장 유사한 정보로 사용자 입력을 대체해.

        사용자 선택한 주문 내역(주문 변경 또는 주문 취소인 경우에만 존재)
        {selected_order}
        판매 중인 상품 목록
        {product_list}
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
).partial(product_list=product_list)
llm =  ChatOpenAI()
request_approval_runnable = request_approval_prompt | llm 


use_order_change_tool_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """
         너는 주문 변경을 처리하는 주문봇이야.
         도구를 사용해 사용자의 요청을 처리해줘.
         사용자의 요청을 꼼꼼히 확인해 도구 호출에 필요한 인자를 정확히 추출해줘.
         사용자의 메시지를 바탕으로 새로운 주문 상세내역을 작성할 때는 판매 상품 목록의 정보와 비교하여 반드시 정확한 정보를 기입. 
         Please provide the order details in the following format:
            items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
            'product_name': The name of the product (str)
            'quantity': The quantity of the product (int)
            'price': The price of the product (float)

         Current user ID: {user_info}
         Product_list: {product_list}
         selected_order: {selected_order}
         """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(product_list=product_list)
llm =  ChatOpenAI()
order_change_tool = [change_order]
use_order_change_tool_runnable = use_order_change_tool_prompt | llm.bind_tools(order_change_tool)


use_order_cancel_tool_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """
         너는 주문 취소를 처리하는 주문봇이야.
         도구를 사용해 사용자의 요청을 처리해줘.
         
         Current user ID: {user_info}
         Product_list: {product_list}
         selected_order: {selected_order}
         """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(product_list=product_list)
llm =  ChatOpenAI()
order_cancel_tool = [cancel_order]
use_order_cancel_tool_runnable = use_order_change_tool_prompt | llm.bind_tools(order_cancel_tool)


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
        ToOrderAssistant,
        ToOrderChangeAssistant,
        ToOrderCancelAssistant,
        ]
    )