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
    ToRequestOrderConfirmation,
    ToHowToChange, ToRequestConfirmation,
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


"""
특히 create_order 사용 시에는 도구 사용에 필요한 사용자 아이디와 사용자의 주문 내역을를 정확하게 파악해야 해.
사용자의 주문 내역은 메시지 기록에서 확인할 수 있어.
Please provide the order details in the following format:
    items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
    'product_name': The name of the product (str)
    'quantity': The quantity of the product (int)
    'price': The price of the product (float)
create_order를 사용해 실제로 주문을 생성하기 전에는 주문을 했다는 거짓말을 하면 안돼.

"""
order_create_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 주문을 생성하는 유능한 주문봇이야.
            적절한 도구를 사용해 고객의 요청을 처리해줘..
            고객이 응답이 필요할 때는 도구를 사용하지 말고 고객에게 응답을 부탁해.
            도구 사용 시 도구 사용에 필요한 인자를 모두 정확하게 추출해줘.
            
            1. 판매 중인 상품 목록을 제시하지 않았다면 fetch_product_list를 사용해.
            2. 고객이 주문할 품목을 말했다면 TodOrderRequestConfirmation를 사용해.
            3. 고객이 주문을 진행하려는 내용에 동의했다면 create_order를 응답으로 출력해.

            user_id: {user_info},
            current time: {time}.
            """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial(time=datetime.now())

order_create_related_tools = [fetch_product_list, ToRequestOrderConfirmation]
order_create_tool = [create_order]
order_create_tools = order_create_related_tools + order_create_tool
order_create_runnable = order_create_prompt | llm.bind_tools(order_create_tools)


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


use_create_tool_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
        """
        너는 사용자 요청대로 새로운 주문을 하는 주문봇이야.
        도구 사용에 필요한 사용자 아이디와 사용자의 주문 내역을를 정확하게 파악해야 해.
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
order_create_tool = [create_order]
use_create_tool_runnable = use_create_tool_prompt | llm.bind_tools(order_create_tool)


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

# order_change_prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             """
#             너는 아래 조건에 따라 정해진 응답을 생성해야 해.
#             메시지 내용이 응답 생성에 영향을 미쳐서는 안돼. 조건에 따라서만 응답을 생성해야 해.
#             - order_id가 주어지지 않은 경우: step1
#             - order_id가 주어지고 request_order_change_message가 주어지지 않은 경우: step2
#             - order_id가 주어지고 request_order_change_message이 True인 경우: step3
#             - order_id가 주어지고 request_order_change_message이 True이며 request_approval_message가 True인 경우: step4

#             응답 전에 조건을 충족하는 응답인지 확실히 확인해줘.
#             응답은 반드시 step1, step2, step3, step4 중 하나여야만 해. 
#             절대 다른 응답을 생성하면 안돼.

#             user_id: {user_info}
#             order_id: {order_id}.
#             request_order_change_message: {request_order_change_message}
#             request_approval_message: {request_approval_message}.
#             current time: {time}.
#             """,
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
# ).partial(time=datetime.now())


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
# ask_order_prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", 
#          """
#          너는 사용자에게 변경할 주문을 묻는 주문봇이야.
#          도구로 생성된 결과를 바탕으로 아래 조건을 만족하는 응답을 작성해줘.
#          1. 응답에는 사용자의 지난 주문 내역이 담겨야 함. 주문 내역에는 주문 날짜, 주문 ID, 상품명, 수량, 가격을 모두 표시.
#          2. 응답에는 변경을 원하는 주문으르 선택해달라는 메시지가 포함되어야 함.
#          """
#          ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
# )

ask_order_runnable = ask_order_prompt | llm 



# ask_order_change_prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", 
#          """
#          너는 사용자에게 주문을 어떻게 변경할지 묻는 주문봇이야.
#          아래 단계에 따라 답변을 생성해.
#          1. 사용자가 선택한 주문 내역을 제시해. 주문 내역에는 주문 ID, 주문 날짜,  상품명, 수량, 가격이 모두 포함되어야 해.
#          2. 사용자에게 주문을 어떻게 변경할지 알려달라고 말해.

         
#          사용자가 선택한 주문 내역
#          {selected_order}
#          """
#          ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
    
# )
ask_order_change_prompt = ChatPromptTemplate.from_messages(
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

ask_order_change_runnable = ask_order_change_prompt | llm 


# request_approval_prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", 
#         """
#         너는 수행할 작업 내용을 확인하는 주문봇이야.
#         아래 단계에 따라 답변을 생성해.
#         아래 단계를 따르지 않은 답변은 절대로 생성해선 안돼.
#         1. 지금까지의 messages를 꼼꼼히 살펴보고 사용자가 요청한 작업을 제시해.
#         2. 너가 파악한 사용자 요청이 맞는지 확인하는 메시지를 추가해. 정확한 상품명, 가격, 수량이 반드시 포함돼야 해.
#         3. 사용자가 요청한 작업이 주문 변경 또는 주문 취소인 경우 사용자가 선택한 주문 내역을 추가해.

#         주의사항
#         사용자의 입력이 상품 목록의 정보와 다른 경우, 상품 목록 가운데 사용자 입력과 가장 유사한 정보로 사용자 입력을 대체해.
#         너는 작업을 실제로 수행할 수는 없어. 사용자가 요청한 작업을 수행했다는 종류의 내용을 답변에 포함해서는 안돼.

#         사용자 선택한 주문 내역(주문 변경 또는 주문 취소인 경우에만 존재)
#         {selected_order}
#         판매 중인 상품 목록
#         {product_list}
#         """
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
    
# ).partial(product_list=product_list)
request_approval_prompt = ChatPromptTemplate.from_messages(
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

request_approval_runnable = request_approval_prompt | llm 


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


# use_order_change_tool_prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", 
#          """
#          너는 주문 변경을 처리하는 주문봇이야.
#          도구를 사용해 사용자의 요청을 처리해줘.
#          사용자의 요청을 꼼꼼히 확인해 도구 호출에 필요한 인자를 정확히 추출해줘.
#          사용자의 메시지를 바탕으로 새로운 주문 상세내역을 작성할 때는 판매 상품 목록의 정보와 비교하여 반드시 정확한 정보를 기입. 
#          Please provide the order details in the following format:
#             items (list[dict[str, str | int | float]]): A list of dictionaries representing the order details. Each dictionary has the following keys:
#             'product_name': The name of the product (str)
#             'quantity': The quantity of the product (int)
#             'price': The price of the product (float)

#          Current user ID: {user_info}
#          Product_list: {product_list}
#          selected_order: {selected_order}
#          """
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
# ).partial(product_list=product_list)

# order_change_tool = [change_order]
# use_order_change_tool_runnable = use_order_change_tool_prompt | llm.bind_tools(order_change_tool)


# use_order_cancel_tool_prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", 
#          """
#          너는 주문 취소를 처리하는 주문봇이야.
#          도구를 사용해 사용자의 요청을 처리해줘.
         
#          Current user ID: {user_info}
#          Product_list: {product_list}
#          selected_order: {selected_order}
#          """
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
# ).partial(product_list=product_list)

# order_cancel_tool = [cancel_order]
# use_order_cancel_tool_runnable = use_order_change_tool_prompt | llm.bind_tools(order_cancel_tool)


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