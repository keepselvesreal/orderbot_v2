from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import tools_condition

from .langgraph_states import State
from .langgraph_assistants import (
    Assistant,
    order_inquiry_runnable,
    order_request_runnable,
    primary_assistant_runnable,
    inquiry_tools, request_tools, primary_assistant_tools,
)
from .langgraph_tools import (
    fetch_user_information, 
    CompleteOrEscalate, ToOrderInquiryAssistant, ToOrderRequestAssistant
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

# This node will be shared for exiting all specialized assistants
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


# order inquiry assistant
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
    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
    if did_cancel:
        return "leave_skill"
    return "inquiry_tools"

builder.add_conditional_edges("order_inquiry", route_order_inquiry)


# order request assistant
builder.add_node(
    "enter_order_request",
    create_entry_node("Order Request Assistant", "order_request"),
)
builder.add_node("order_request", Assistant(order_request_runnable))
builder.add_edge("enter_order_request", "order_request")
builder.add_node(
    "request_tools",
    create_tool_node_with_fallback(request_tools),
)
builder.add_edge("request_tools", "order_request")

def route_order_inquiry(
        state: State,
) -> Literal[
    "request_tools",
    "leave_skill",
    "__end__"
]:
    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
    if did_cancel:
        return "leave_skill"
    return "request_tools"

builder.add_conditional_edges("order_request", route_order_inquiry)


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
    "enter_order_request",
    "__end__",
]:
    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        if tool_calls[0]["name"] == ToOrderInquiryAssistant.__name__:
            return "enter_order_inquiry"
        elif tool_calls[0]["name"] == ToOrderRequestAssistant.__name__:
            return "enter_order_request"
        return "primary_assistant_tools"
    raise ValueError("Invalid route")

builder.add_conditional_edges(
    "primary_assistant",
    route_primary_assistant,
    {
        "enter_order_inquiry": "enter_order_inquiry",
        "enter_order_request": "enter_order_request",
        "primary_assistant_tools": "primary_assistant_tools",
        END: END,
    },
)


# Each delegated workflow can directly respond to the user
# When the user responds, we want to return to the currently active workflow
def route_to_workflow(
    state: State,
) -> Literal[
    "primary_assistant",
    "order_inquiry",
    "order_request",
]:
    """If we are in a delegated state, route directly to the appropriate assistant."""
    dialog_state = state.get("dialog_state")
    if not dialog_state:
        return "primary_assistant"
    return dialog_state[-1]

builder.add_conditional_edges("fetch_user_info", route_to_workflow)


memory = SqliteSaver.from_conn_string(":memory:")
orderbot_graph = builder.compile(
    checkpointer=memory,
    interrupt_before=[
        "request_tools",
    ],
)