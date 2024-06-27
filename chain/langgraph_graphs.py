from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import tools_condition

from .langgraph_states import State
from .langgraph_assistants import (
    Assistant,
    order_create_runnable,
    present_product_list_runnable,
    use_create_tool_runnable,
    create_tool,
    order_inquiry_runnable,
    inquiry_tools,
    order_update_runnable,
    ask_order_runnable,
    request_approval_runnable,
    use_update_tool_runnable,
    update_tools,
    primary_assistant_runnable,
    primary_assistant_tools,
)
from .langgraph_tools import (
    fetch_user_information, 
    fetch_product_list,
    fetch_recent_order,
    CompleteOrEscalate,
    ToOrderAssistant, 
    ToOrderInquiryAssistant, 
    ToOrderUpdateAssistant
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
    "order_update",
    "order_create"
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


def create_order_route(state: State):
    print("-"*77)
    print("create_order_route 진입")
    print("state\n", state)
    
    response = state["messages"][-1].content
    print("response: ", response)
    if response == "present_product_list":
        return "present_product_list"
    elif response == "request_approval":
        return "request_approval"
    elif response == "use_create_tool":
        return "use_create_tool"
    
builder.add_conditional_edges(
    "order_create",
    create_order_route,
    {
        "present_product_list": "present_product_list",
        "request_approval": "request_approval",
        "use_create_tool": "use_create_tool",
    },
)


def present_product_list(state: State):
    print("-"*77)
    print("present_product_list 진입")
    print("state\n", state)

    messages = state["messages"]
    product_list = fetch_product_list()
    response = present_product_list_runnable.invoke({"messages": messages,
                                                     "product_list": product_list})
    response = response.content

    return {"messages": response, "product_presentation": True} 

builder.add_node("present_product_list", present_product_list)
builder.add_edge("present_product_list", END)


def reset_state_without_messages(state: State):
    messages = state["messages"]
    sub_state = state.copy()
    sub_state.update({key: None for key in sub_state.keys() if key not in ["messages", "dialog_state"]})
    return {**sub_state, "messages": messages, "dialog_state": "pop"}

builder.add_node("reset_state_without_messages", reset_state_without_messages)


builder.add_node("use_create_tool", Assistant(use_create_tool_runnable))
builder.add_node(
    "create_tool",
    create_tool_node_with_fallback(create_tool)
    )
builder.add_edge("use_create_tool", "create_tool")
builder.add_edge("create_tool", "reset_state_without_messages")


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
builder.add_edge("inquiry_tools", "order_inquiry")


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
# order update sub-graph
builder.add_node(
    "enter_order_update",
    create_entry_node("Order Update Assistant", "order_update"),
)
builder.add_node("order_update", Assistant(order_update_runnable))
builder.add_edge("enter_order_update", "order_update")


def update_order_route(state: State):
    print("-"*77)
    print("update_order_route 진입")
    print("state\n", state)
    
    response = state["messages"][-1].content
    if response == "display_user_order":
        return "display_user_order"
    elif response == "request_approval":
        return "request_approval"
    elif response == "use_update_tools":
        return "use_update_tools"
    
builder.add_conditional_edges(
    "order_update",
    update_order_route,
    {
        "display_user_order": "display_user_order",
        "request_approval": "request_approval",
        "use_update_tools": "use_update_tools",
    },
)


def display_user_order(state: State):
    print("-"*77)
    print("display_user_order 진입")
    print("state\n", state)

    user_id = state["user_info"]
    print("user_id\n", user_id)
    recent_orders = fetch_recent_order({"user_id": user_id})
    response = ask_order_runnable.invoke({**state, "orders": recent_orders})
    response = response.content

    return {"messages": response, "orders": recent_orders}

builder.add_node("display_user_order", display_user_order)
builder.add_edge("display_user_order", END)


def request_approval(state: State):
    print("-"*77)
    print("request_approval 진입")
    print("state\n", state)

    orders = state["orders"]
    # product_list = fetch_product_list()
    messages = state["messages"]
    response = request_approval_runnable.invoke({"orders": orders, 
                                                 "messages": messages})
    return {"messages": response, "request_approval_message": True}

builder.add_node("request_approval", request_approval)
builder.add_edge("request_approval", END)

builder.add_node("use_update_tools", Assistant(use_update_tool_runnable))
builder.add_node(
    "update_tools",
    create_tool_node_with_fallback(update_tools)
    )
builder.add_edge("use_update_tools", "update_tools")
builder.add_edge("update_tools", "reset_state_without_messages")
builder.add_edge("reset_state_without_messages", END)


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
    "enter_order_update",
    "enter_order_create"
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
        elif tool_calls[0]["name"] == ToOrderUpdateAssistant.__name__:
            return "enter_order_update"
        elif tool_calls[0]["name"] == ToOrderAssistant.__name__:
            return "enter_order_create"
        return "primary_assistant_tools"
    raise ValueError("Invalid route")

builder.add_conditional_edges(
    "primary_assistant",
    route_primary_assistant,
    {
        "enter_order_inquiry": "enter_order_inquiry",
        "enter_order_update": "enter_order_update",
        "enter_order_create": "enter_order_create",
        "primary_assistant_tools": "primary_assistant_tools",
        END: END, # 도구 바로 사용하는 enter_order_inquiry 때문에 내비둬야 하나?
    },
)


memory = SqliteSaver.from_conn_string(":memory:")
orderbot_graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["create_tool", "update_tools"]
)