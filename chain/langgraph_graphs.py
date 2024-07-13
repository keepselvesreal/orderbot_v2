from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import tools_condition

from .langgraph_states import State
from .langgraph_assistants import (
    Assistant,
    order_create_runnable,
    request_order_confirmation_runnable,
    present_product_list_runnable,
    order_create_related_tools,
    order_create_tool,

    order_inquiry_runnable,
    inquiry_tools,

    order_change_runnable,
    ask_order_runnable,
    ask_how_to_change_runnable,
    request_order_change_confirmation_runnable,
    order_change_related_tools,
    order_change_tool,

    order_cancel_runnable,
    request_order_cancel_confirmation_runnable,
    order_cancel_related_tools,
    order_cancel_tool,

    primary_assistant_runnable,
    primary_assistant_tools,
    
)
from .langgraph_tools import (
    fetch_user_information, 
    fetch_product_list,
    fetch_recent_order,
    CompleteOrEscalate,
    ToOrderInquiryAssistant, 
    ToOrderAssistant, 
    ToOrderChangeAssistant,
    ToOrderCancelAssistant,

    ToHowToChange, 
    ToRequestConfirmation,
)

from .langgraph_utilities import create_entry_node, create_tool_node_with_fallback


builder = StateGraph(State)


def user_info(state: State):
    print("-"*77)
    print("user_info 진입")
    user_id = state["user_info"]
    return {"user_info": fetch_user_information.invoke({"user_id": user_id})}

builder.add_node("fetch_user_info", user_info)
builder.set_entry_point("fetch_user_info")


def route_to_workflow(
    state: State,
) -> Literal[
    "primary_assistant",
    "order_inquiry",
    "order_create",
    "order_change",
    "order_cancel",
]:
    """If we are in a delegated state, route directly to the appropriate assistant."""
    print("-"*77)
    print("route_to_workflow 진입")
    print("state\n", state)
    
    dialog_state = state.get("dialog_state")
    if not dialog_state:
        return "primary_assistant"
    return dialog_state[-1]

builder.add_conditional_edges("fetch_user_info", route_to_workflow)


# order_inquiry sub-graph에서 사용
def pop_dialog_state(state: State) -> dict:
    """Pop the dialog stack and return to the main assistant.

    This lets the full graph explicitly track the dialog flow and delegate control
    to specific sub-graphs.
    """
    messages = []
    if state["messages"][-1].tool_calls:
        # Note: Doesn't currently handle the edge case where the llm performs parallel tool calls
        messages.append(
            ToolMessage(
                content="Resuming dialog with the host assistant. Please reflect on the past conversation and assist the user as needed.",
                tool_call_id=state["messages"][-1].tool_calls[0]["id"],
            )
        )
    return {
        "dialog_state": "pop",
        "messages": messages,
    }

builder.add_node("leave_skill", pop_dialog_state)
builder.add_edge("leave_skill", "primary_assistant")

#--------------------------------------------------------------------------------------------------------------------------------------
# order create sub-graph
builder.add_node(
    "enter_order_create",
    create_entry_node("Order Create Assistant", "order_create"),
)


builder.add_node("order_create", Assistant(order_create_runnable))


builder.add_edge("enter_order_create", "order_create")


def order_create_route(state):
    print("-"*70)
    print("order_create_route 진입")
    route = tools_condition(state)
    if route == END:
        return END
    
    tool_calls = state["messages"][-1].tool_calls
    print("tool_name_to_call: ", tool_calls[0]["name"])
    did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
    if did_cancel:
        return "leave_skill"
    elif tool_calls[0]["name"] == "create_order":
        return "order_create_tool"

    return "order_create_related_tools"


builder.add_conditional_edges("order_create", order_create_route)


builder.add_node(
    "order_create_related_tools",
    create_tool_node_with_fallback(order_create_related_tools)
    )


def order_create_related_tools_route(state):
     print("-"*70)
     print("order_create_tools_route 진입")
     tool_message = state["messages"][-1]
     tool_name = tool_message.name
     print("tool_message\n", tool_message)
     print("tool_name: ", tool_message.name)

     if tool_name == "fetch_product_list":
         return "present_product_list"
     elif tool_name == ToRequestConfirmation.__name__:
         return "request_order_confirmation"


builder.add_conditional_edges("order_create_related_tools", order_create_related_tools_route)


builder.add_node(
    "order_create_tool",
    create_tool_node_with_fallback(order_create_tool)
    )


builder.add_edge("order_create_tool", "reset_state_without_messages")


builder.add_edge("reset_state_without_messages", END)


def present_product_list(state: State):
    print("-"*77)
    print("present_product_list 진입")
    print("state\n", state)

    messages = state["messages"]
    response = present_product_list_runnable.invoke({"messages": messages})
    response = response.content

    return {"messages": response} 


builder.add_node("present_product_list", present_product_list)


builder.add_edge("present_product_list", END)


def request_order_confirmation(state: State):
    print("-"*77)
    print("request_order_confirmation 진입")
    print("state\n", state)

    messages = state["messages"]
    response = request_order_confirmation_runnable.invoke({"messages": messages})
    
    return {"messages": response}


builder.add_node("request_order_confirmation", request_order_confirmation)


builder.add_edge("request_order_confirmation", END)


# 현재 사용되고 있지 않은 노드
def extract_args_for_create_order(state: State):
    print("-"*77)
    print("extract_args_for_create_order 진입")
    print("state\n", state)

    messages = state["messages"]
    user_info = state["user_info"]
    
    pass

# builder.add_node("extract_args_for_create_order", extract_args_for_create_order)
# builder.add_edge("extract_args_for_create_order", "order_create_tool")


def reset_state_without_messages(state: State):
    messages = state["messages"]
    sub_state = state.copy()
    sub_state.update({key: None for key in sub_state.keys() if key not in ["messages", "dialog_state"]})
    return {**sub_state, "messages": messages, "dialog_state": "pop"}

builder.add_node("reset_state_without_messages", reset_state_without_messages)


#--------------------------------------------------------------------------------------------------------------------------------------
# order inquiry sub-graph
builder.add_node(
    "enter_order_inquiry",
    create_entry_node("Order Inqury Assistant", "order_inquiry"),
)


builder.add_node("order_inquiry", Assistant(order_inquiry_runnable))


builder.add_edge("enter_order_inquiry", "order_inquiry")


builder.add_node(
    "inquiry_tools",
    create_tool_node_with_fallback(inquiry_tools),
)


builder.add_edge("inquiry_tools", END)


def route_order_inquiry(
        state: State,
) -> Literal[
    "inquiry_tools",
    "leave_skill",
    "__end__"
]:
    print("-"*77)
    print("route_order_inquiry 진입")
    print("state\n", state)

    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
    if did_cancel:
        return "leave_skill"
    return "inquiry_tools"


builder.add_conditional_edges("order_inquiry", route_order_inquiry)


#--------------------------------------------------------------------------------------------------------------------------------------
# order change sub-graph
builder.add_node(
    "enter_order_change",
    create_entry_node("Order Change Assistant", "order_change"),
)

builder.add_node("order_change", Assistant(order_change_runnable))
builder.add_edge("enter_order_change", "order_change")


def order_change_route(state):
    print("-"*70)
    print("order_change_route 진입")
    route = tools_condition(state)
    if route == END:
        return END
    
    tool_calls = state["messages"][-1].tool_calls
    print("tool_name_to_call: ", tool_calls[0]["name"])
    did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
    if did_cancel:
        return "leave_skill"
    elif tool_calls[0]["name"] == "change_order":
        return "order_change_tool"
    return "order_change_related_tools"

builder.add_conditional_edges("order_change", order_change_route)


builder.add_node(
    "order_change_related_tools", create_tool_node_with_fallback(order_change_related_tools)
)


def order_change_related_tools_route(state):
     print("-"*70)
     print("order_change_tools_route 진입")
     tool_message = state["messages"][-1]
     tool_name = tool_message.name
     print("tool_message\n", tool_message)
     print("tool_name: ", tool_message.name)
     
     if tool_name == "fetch_recent_order":
         return "display_user_order"
     elif tool_name == ToHowToChange.__name__:
        return "ask_how_to_change"
     elif tool_name == ToRequestConfirmation.__name__:
         return "request_comfirmation"
     

builder.add_conditional_edges("order_change_related_tools", order_change_related_tools_route)


builder.add_node(
    "order_change_tool", create_tool_node_with_fallback(order_change_tool)
)


builder.add_edge("order_change_tool", "reset_state_without_messages")


builder.add_edge("reset_state_without_messages", END)


def display_user_order(state: State):
    import json
    print("-"*77)
    print("display_user_order 진입")
    print("state\n", state)

    messages = state["messages"]
    tool_result = state["messages"][-1]
    print("tool_result\n", tool_result)
    orders = tool_result.content
    orders = json.loads(orders)
    print("="*70)
    print("orders\n", orders)
    user_id = state["user_info"]
    recent_orders = fetch_recent_order({"user_id": user_id})
    print("="*70)
    print("recent_orders\n", recent_orders)
    output = ask_order_runnable.invoke({"messages": messages,
                                        "orders": orders})
    response = output.content
    print("response\n", response)

    return {"messages": response, "orders": recent_orders}


builder.add_node("display_user_order", display_user_order)


builder.add_edge("display_user_order", END)


def ask_how_to_change(state: State):
    print("-"*77)
    print("ask_how_to_change 진입")
    print("state\n", state)

    messages = state["messages"]
    response = ask_how_to_change_runnable.invoke({"messages": messages})
    
    return {"messages": response}


builder.add_node("ask_how_to_change", ask_how_to_change)


builder.add_edge("ask_how_to_change", END)


def request_order_change_confirmation(state: State):
    print("-"*77)
    print("request_confirmation 진입")
    print("state\n", state)

    messages = state["messages"]
    response = request_order_change_confirmation_runnable.invoke({"messages": messages})
    
    return {"messages": response}


builder.add_node("request_confirmation", request_order_change_confirmation)


builder.add_edge("request_confirmation", END)


#--------------------------------------------------------------------------------------------------------------------------------------
# order cancel sub-graph
builder.add_node(
    "enter_order_cancel",
    create_entry_node("Order Cancel Assistant", "order_cancel"),
)


builder.add_node("order_cancel", Assistant(order_cancel_runnable))


builder.add_edge("enter_order_cancel", "order_cancel")


def order_cancel_route(state):
    print("-"*70)
    print("order_cancel_route 진입")
    route = tools_condition(state)
    if route == END:
        return END
    
    tool_calls = state["messages"][-1].tool_calls
    print("tool_name_to_call: ", tool_calls[0]["name"])
    did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
    if did_cancel:
        return "leave_skill"
    elif tool_calls[0]["name"] == "cancel_order":
        return "order_cancel_tool"
    return "order_cancel_related_tools"


builder.add_conditional_edges("order_cancel", order_cancel_route)


builder.add_node(
    "order_cancel_related_tools", create_tool_node_with_fallback(order_cancel_related_tools)
)


def order_cancel_related_tools_route(state):
     print("-"*70)
     print("order_cancel_tools_route 진입")
     
     tool_message = state["messages"][-1]
     tool_name = tool_message.name
     print("tool_message\n", tool_message)
     print("tool_name: ", tool_message.name)
     
     if tool_name == "fetch_recent_order":
         return "display_user_order"
     elif tool_name == ToRequestConfirmation.__name__:
         return "request_order_cancel_confirmation"
     

builder.add_conditional_edges("order_cancel_related_tools", order_cancel_related_tools_route)


builder.add_node(
    "order_cancel_tool", create_tool_node_with_fallback(order_cancel_tool)
)


builder.add_edge("order_cancel_tool", "reset_state_without_messages")


builder.add_edge("reset_state_without_messages", END)


def request_order_cancel_confirmation(state: State):
    print("-"*77)
    print("request_order_cancel_confirmation 진입")
    print("state\n", state)

    messages = state["messages"]
    response = request_order_cancel_confirmation_runnable.invoke({"messages": messages})

    return {"messages": response}


builder.add_node("request_order_cancel_confirmation", request_order_cancel_confirmation)


builder.add_edge("request_order_cancel_confirmation", END)


#'--------------------------------------------------------------------------------------------------------------------------------------
# Primary assistant
builder.add_node("primary_assistant", Assistant(primary_assistant_runnable))


builder.add_node(
    "primary_assistant_tools", create_tool_node_with_fallback(primary_assistant_tools)
)


builder.add_edge("primary_assistant_tools", "primary_assistant")


def route_primary_assistant(
        state: State,
) -> Literal[
    "primary_assistant_tools",
    "enter_order_inquiry",
    "enter_order_create",
    "enter_order_change",
    "enter_order_cancel",
    "__end__",
]:
    print("-"*77)
    print("route_primary_assistant 진입")
    print("state\n", state)

    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        if tool_calls[0]["name"] == ToOrderInquiryAssistant.__name__:
            return "enter_order_inquiry"
        elif tool_calls[0]["name"] == ToOrderAssistant.__name__:
            return "enter_order_create"
        elif tool_calls[0]["name"] == ToOrderChangeAssistant.__name__:
            return "enter_order_change"
        elif tool_calls[0]["name"] == ToOrderCancelAssistant.__name__:
            return "enter_order_cancel"
        return "primary_assistant_tools"
    raise ValueError("Invalid route")


builder.add_conditional_edges(
    "primary_assistant",
    route_primary_assistant,
    {
        "enter_order_inquiry": "enter_order_inquiry",
        "enter_order_create": "enter_order_create",
        "enter_order_change": "enter_order_change",
        "enter_order_cancel": "enter_order_cancel",
        "primary_assistant_tools": "primary_assistant_tools",
        END: END, # 도구 바로 사용하는 enter_order_inquiry 때문에 내비둬야 하나?
    },
)


memory = SqliteSaver.from_conn_string(":memory:")


orderbot_graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["order_create_tool", "order_change_tool", "order_cancel_tool"]
)