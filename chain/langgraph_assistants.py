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
    get_all_orders, get_changeable_orders, fetch_recent_order, get_change_order, get_cancel_order, 
    create_order, change_order, cancel_order,
    
    # GPT는 아래 pydantic model을 user_request.py로 빼는 걸 추천
    CompleteOrEscalate, 

    ToOrderAssistant, ToOrderChangeAssistant, ToOrderCancelAssistant, ToOrderInquiryAssistant,
    
    ExtractOrderArgs,

    ToHowToChange, 
    ToRequestConfirmation,
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
            너는 주문을 생성하는 유능한 주문봇이야.
            적절한 도구를 사용해 고객의 요청을 처리해줘..
            고객이 응답이 필요할 때는 도구를 사용하지 말고 고객에게 응답을 부탁해.
            도구 사용 시 도구 사용에 필요한 인자를 모두 정확하게 추출해야 해.
            도구 사용에 필요한 인자는 아래 메시지에서 추출하면 돼.
            
            1. 판매 중인 상품 목록을 제시하지 않았다면 fetch_product_list 도구를 사용해.
            2. 고객이 주문할 품목을 말했다면 TodOrderRequestConfirmation 도규를 사용해.
            3. 고객이 주문을 진행하려는 내용에 동의했다면 ExtractOrderArgs 도구를 사용해.

            user_id: {user_info},
            current time: {time}.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

order_create_related_tools = [fetch_product_list, ToRequestConfirmation, ExtractOrderArgs]
order_create_tool = [create_order]
# order_create_tools = order_create_related_tools + order_create_tool
order_create_runnable = order_create_prompt | llm.bind_tools(order_create_related_tools)


present_product_list_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 사용자에게 판매 중인 상품을 알려주는 안내봇이야.
        ToolMessage에 담긴 정보를 바탕으로 판매 중인 상품 목록을 알기 쉽게 제시해줘.
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
)
present_product_list_runnable = present_product_list_prompt | llm


request_order_confirmation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 사용자의 요청 사항을 확인하는 주문봇이야.
        ToolMessage에 담긴 정보를 바탕으로 아례 예시처럼 응답을 생성해줘.
        응답에는 반드시 상품명, 가격, 수량을 모두 포함해야 해.
        응답을 출력하기 전에 응답에 상품명, 가격, 수량이 모두 포함돼 있는지 확인하고, 깜빡했다면 반드시 포함시켜줘.

        # ToolMessage에 담긴 정보 예시
        product_list: 떡케익5호 - 54,000원, 무지개 백설기 케익 - 51,500원, 미니 백설기 (35개 세트) - 31,500원, 개별 모듬팩 - 13,500원
        customer_order_request: 미니 백설기 1개, 개별 모듬팩 2개
        message_to_be_confirmed: 미니 백설기 1개 - 31,500원, 개별 모듬팩 2개 - 27,000원

        # 모델 응답 예시

        주문 품목:
        1. 상품명: 미니 백설기 
           가격: 31,500원 
           수량: 1개

        2. 상품명: 개별 모듬팩
           가격: 13,500원
           수량: 2개

           총 가격: 31,500+27,000 = 58,500원
        
        이대로 주문을 진행하면 될까요?
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
)
request_order_confirmation_runnable = request_order_confirmation_prompt | llm


extract_args_for_create_order_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
)


# order inquiry assistant
order_inquiry_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a specialized assistant for handling order queries.
            The primary assistant delegates work to you whenever the user needs help with their orders.
            일반적인 주문 조회 요청 경우에는 get_all_orders 도구를 사용해.
            변경한 주문에 대한 조회를 요청한 경우에는 get_chage_order 도구를 사용해.
            취소한 주문에 대한 조회를 요청한 경우에는 get_cancel_order 도구를 사용해.
            
            user_id: {user_info}
            current_time: {time}.

            If you need more information or the customer changes their mind, escalate the task back to the main assistant.
            If the user needs help, and none of your tools are appropriate for it, then 'CompleteOrEscalate' the dialog to the host assistant. Do not waste the user's time. Do not make up invalid tools or functions.
            Do not make up or fabricate any details. Respond honestly if you lack the necessary information to address the user's query.
            """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

inquiry_tools = [get_all_orders, get_change_order, get_cancel_order]
order_inquiry_runnable = order_inquiry_prompt | llm.bind_tools(   
    inquiry_tools + [CompleteOrEscalate]
)
order_inquiry_runnable


order_change_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 주문 변경을 담당하는 유능한 비서야.
            적절한 도구를 사용해 고객의 요청을 처리해.
            고객이 응답이 필요할 때는 도구를 사용하지 말고 고객에게 응답을 부탁해.

            고객에게 변경할 기존 주문 내역을 제시하지 않았다면 fetch_recent_order를 사용해.
            고객이 변경할 주문을 선택한 다음에는 ToHowToChange를 사용해.
            고객이 어떻게 주문을 변경할지 말한 다음에는 TodRequestApproval를 사용해.
            고객이 진행할 주문 변경을 승인했다면 change_order를 사용해.

            user_id: {user_info},
            selected_order: {selected_order}
            current time: {time}.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

# order_change_related_tools = [fetch_recent_order, ask_how_to_change, request_approval, change_order]
order_change_related_tools = [fetch_recent_order, ToHowToChange, ToRequestConfirmation]
order_change_tool = [change_order]
order_change_tools = order_change_related_tools + order_change_tool
order_change_agent_with_tools = llm.bind_tools(tools=order_change_tools
                                               + [
                                                   CompleteOrEscalate,
                                               ])
# order_change_runnable = order_change_prompt | llm
order_change_runnable = order_change_prompt | order_change_agent_with_tools


order_cancel_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 주문 변경을 담당하는 유능한 비서야.
            적절한 도구를 사용해 고객의 요청을 처리해.
            도구를 사용할 때는 도구 사용 조건을 확실히 확인한 후 조건을 충족할 때만 사용하도록 주의해줘.
            고객이 응답이 필요할 때는 도구를 사용하지 말고 고객에게 응답을 부탁해.

            취소할 주문을 선택할 수 있는 기존 주문 내역을 제시하지 않았다면 fetch_recent_order를 사용해.
            고객이 취소할 주문을 선택했다면 ToRequestConfirmation를 사용해.
            고객이 취소할 주문을 확인했다면 cancel_order를 사용해.


            user_id: {user_info},
            selected_order: {selected_order}
            current time: {time}.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

order_cancel_related_tools = [fetch_recent_order, ToRequestConfirmation]
order_cancel_tool = [cancel_order]
order_cancel_tools = order_cancel_related_tools + order_cancel_tool
order_cancel_runnable = order_cancel_prompt | llm.bind_tools(order_cancel_tools)


ask_order_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """
         너는 사용자에게 변경할 주문을 묻는 주문봇이야.
         아래 단계에 따라 답변을 생성해.
         1. 사용자의 지난 주문 내역을 표시해. 주문 내역에는 주문 날짜, 주문 ID, 상품명, 수량, 가격을 모두 표시해.
         2. 사용자에게 변경을 원하는 주문으르 선택해달라는 메시지를 작성해.
         
         사용자 지난 주문 내역
         {orders}
         """
         ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

ask_order_runnable = ask_order_prompt | llm 


ask_how_to_change_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """
        너는 고객에게 주문을 어떻게 변경할지 물어보는 주문봇이야.
        ToolMessage에 담긴 정보를 바탕으로 아례 예시처럼 응답을 생성해줘.

        <예시>
        # ToolMessage의 selected_order에 담긴 정보
        Order ID: 100, Status: order_changed, Created At: 2024-07-08T14:10:22.417655+00:00<br>Items:<ul><li>미니 백설기 - Quantity: 2, Price: 31500</li></ul>

        # 모델 응답 예시
        <고객이 선택한 주문 내역>

        주문 ID: 100
        기존 주문 상태: 주문 변경, 
        주문 생성일: 2024년 7월 8일 오후 2시 10분 22초
        주문 품목:
        1. 상품명: 미니 백설기 
           가격: 31,500원 
           수량: 2개 
           총 가격: 63,000원
        
        이 주문 내역을 어떻게 변경하길 원하시나요?
         """
         ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
)

ask_how_to_change_runnable =ask_how_to_change_prompt | llm 


request_order_change_confirmation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 사용자의 요청 사항을 확인하는 주문봇이야.
        ToolMessage에 담긴 정보를 바탕으로 아례 예시처럼 응답을 생성해줘.
        응답에는 반드시 사용자가 선택한 주문과 사용자의 요청사항을 포함해야 해.

        <예시>
        # ToolMessage에 담긴 정보 예시
        ## selected_order 필드에 담긴 정보
        Order ID: 100, Status: order_changed, Created At: 2024-07-08T14:10:22.417655+00:00
        Items:
        미니 백설기 - Quantity: 2, Price: 31,500
        
        ## customer_request 필드에 담긴 정보
        'Add 1 떡케익' 
        
        ## message_to_be_approved 필드에 담긴 정보
        Please confirm the following changes to your order:
        Selected Order: Order ID: 100, Status: order_changed, Created At: 2024-07-08T14:10:22.417655+00:00
        Items:
        미니 백설기 - Quantity: 2, Price: 31,500

        # 모델 응답 예시
        <고객이 선택한 주문 내역>

        주문 ID: 100
        기존 주문 상태: 주문 변경, 
        주문 생성일: 2024년 7월 8일 오후 2시 10분 22초
        주문 품목:
        1. 상품명: 미니 백설기 
           가격: 31,500원 
           수량: 2개 
           
           총 가격: 63,000원


       <사용자가 새로 주문한 내역>

       주문 품목:
        1. 상품명: 미니 백설기 
           가격: 31,500원 
           수량: 1개

        2. 상품명: 개별 모듬팩
           가격: 13,500원
           수량: 2개

           총 가격: 31,500+27,000 = 58,500원
        
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
).partial(product_list=product_list)

request_order_change_confirmation_runnable = request_order_change_confirmation_prompt | llm 


request_order_cancel_confirmation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 사용자의 요청 사항을 확인하는 주문봇이야.
        ToolMessage에 담긴 정보를 바탕으로 아례 예시처럼 응답을 생성해줘.

        <예시>
        # ToolMessage에 담긴 정보 예시
        ## selected_order 필드에 담긴 정보
        Order ID: 100, Status: order_changed, Created At: 2024-07-08T14:10:22.417655+00:00
        Items:
        미니 백설기 - Quantity: 2, Price: 31,500
        
        ## customer_request 필드에 담긴 정보
        I would like to cancel this order.
        
        ## message_to_be_approved 필드에 담긴 정보
        아니요, 그 문장은 맞지 않습니다. 영어로 "Please confirm the cancellation of your order
        Selected Order: Order ID: 100, Status: order_changed, Created At: 2024-07-08T14:10:22.417655+00:00
        Items:
        미니 백설기 - Quantity: 2, Price: 31,500

        # 모델 응답 예시
        <고객이 선택한 주문 내역>

        주문 ID: 100
        기존 주문 상태: 주문 변경, 
        주문 생성일: 2024년 7월 8일 오후 2시 10분 22초
        주문 품목:
        1. 상품명: 미니 백설기 
           가격: 31,500원 
           수량: 2개 
           
           총 가격: 63,000원

       이 주문을 취소하시겠습니까?
        """
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
    
).partial(product_list=product_list)

request_order_cancel_confirmation_runnable = request_order_cancel_confirmation_prompt | llm 


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