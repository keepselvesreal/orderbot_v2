from typing import Literal
from langgraph.prebuilt import tools_condition
from langgraph.graph import END


from .states import State
from .tools import (
    CompleteOrEscalate,
    ToOrderInquiryAssistant,
    ToOrderAssistant,
    ToOrderChangeAssistant,
    ToOrderCancelAssistant,
    ToRequestOrderConfirmation,
    ToHowToChange,
    ToRequestOrderChangeConfirmation,
    ToRequestOrderCancelConfirmation,

)


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


def route_primary_assistant(
        state: State,
) -> Literal[
    "primary_assistant_tools",
    "enter_order_inquiry",
    "enter_order_create",

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


def order_create_related_tools_route(state):
     print("-"*70)
     print("order_create_tools_route 진입")

     tool_message = state["messages"][-1]
     tool_name = tool_message.name
     print("tool_message\n", tool_message)
     print("tool_name: ", tool_message.name)

     if tool_name == "fetch_product_list":
         return "present_product_list"
     elif tool_name == ToRequestOrderConfirmation.__name__:
         return "request_order_confirmation"


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
     elif tool_name == ToRequestOrderChangeConfirmation.__name__:
         return "request_order_change_confirmation"
     

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


def order_cancel_related_tools_route(state):
     print("-"*70)
     print("order_cancel_tools_route 진입")
     
     tool_message = state["messages"][-1]
     tool_name = tool_message.name
     print("tool_message\n", tool_message)
     print("tool_name: ", tool_message.name)
     
     if tool_name == "fetch_recent_order":
         return "display_user_order"
     elif tool_name == ToRequestOrderCancelConfirmation.__name__:
         return "request_order_cancel_confirmation"