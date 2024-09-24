from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import AIMessage
from django.db.models import QuerySet

from .prompts import (
    primary_assistant_prompt,
    order_inquiry_prompt,
    order_create_prompt,
    present_product_list_prompt,
    request_order_confirmation_prompt,
    order_change_prompt,
    ask_order_prompt,
    ask_how_to_change_prompt,
    request_order_change_confirmation_prompt,
    order_cancel_prompt,
    request_order_cancel_confirmation_prompt
)
from .states import State
from product.models import Order
from .tools import (
    get_all_orders, get_change_order,get_cancel_order, 
    CompleteOrEscalate,
    lookup_policy, fetch_product_list, 
    
    ToRequestOrderConfirmation,
    create_order,

    fetch_recent_order,
    ToHowToChange,
    ToRequestOrderChangeConfirmation,
    change_order,

    ToRequestOrderCancelConfirmation,
    cancel_order,
    
    ToOrderInquiryAssistant, ToOrderAssistant, ToOrderChangeAssistant, ToOrderCancelAssistant,
    )


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

        elif isinstance(result, QuerySet):
            result = [order.to_dict() for order in result]
            result = AIMessage(content=result)
        
        add_state = {k: v for k, v in state.items() if k != "dialog_state"}
        
        return {**add_state, "messages": result}
    

#--------------------------------------------------------------------------------------------------------------------------------------
# order inquiry related things



inquiry_tools = [get_all_orders, get_change_order, get_cancel_order]
order_inquiry_runnable = order_inquiry_prompt | llm.bind_tools(   
    inquiry_tools + [CompleteOrEscalate]
)
order_inquiry_runnable




order_create_related_tools = [fetch_product_list, ToRequestOrderConfirmation]
order_create_tool = [create_order]
order_create_tools = order_create_related_tools + order_create_tool
order_create_runnable = order_create_prompt | llm.bind_tools(order_create_tools)
# order_create_runnable = order_create_prompt | llm.bind_tools(order_create_related_tools)
# order_create_runnable = order_create_prompt | llm.bind_tools(order_create_tool)


present_product_list_runnable = present_product_list_prompt | llm



request_order_confirmation_runnable = request_order_confirmation_prompt | llm


#--------------------------------------------------------------------------------------------------------------------------------------
# order change related things



# order_change_related_tools = [fetch_recent_order, ask_how_to_change, request_approval, change_order]
order_change_related_tools = [fetch_recent_order, ToHowToChange, ToRequestOrderChangeConfirmation]
order_change_tool = [change_order]
order_change_tools = order_change_related_tools + order_change_tool
order_change_agent_with_tools = llm.bind_tools(tools=order_change_tools
                                               + [
                                                   CompleteOrEscalate,
                                               ])
# order_change_runnable = order_change_prompt | llm
order_change_runnable = order_change_prompt | order_change_agent_with_tools




ask_order_runnable = ask_order_prompt | llm 




ask_how_to_change_runnable =ask_how_to_change_prompt | llm 




request_order_change_confirmation_runnable = request_order_change_confirmation_prompt | llm 


#--------------------------------------------------------------------------------------------------------------------------------------
# order cancel related things



order_cancel_related_tools = [fetch_recent_order, ToRequestOrderCancelConfirmation]
order_cancel_tool = [cancel_order]
order_cancel_tools = order_cancel_related_tools + order_cancel_tool
order_cancel_runnable = order_cancel_prompt | llm.bind_tools(order_cancel_tools)




request_order_cancel_confirmation_runnable = request_order_cancel_confirmation_prompt | llm 


#--------------------------------------------------------------------------------------------------------------------------------------
# primary assistant related things



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