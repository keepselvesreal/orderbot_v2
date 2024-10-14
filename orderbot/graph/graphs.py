from langgraph.graph import StateGraph
from langgraph.graph import END
from langgraph.checkpoint.sqlite import SqliteSaver

from .states import State
from .nodes import (
    user_info,
    pop_dialog_state,
    present_product_list,
    request_order_confirmation,
    reset_state_without_messages,
    display_user_order,
    ask_how_to_change,
    request_order_change_confirmation,
    request_order_cancel_confirmation,

)
from .routes import (
    route_to_workflow,
    route_order_inquiry,
    order_create_route,
    order_create_related_tools_route,
    order_change_route,
    order_change_related_tools_route,
    order_cancel_route,
    order_cancel_related_tools_route,
    route_primary_assistant,
)
from .utilities import create_entry_node, create_tool_node_with_fallback
from .runnables import (
    Assistant, 
    order_inquiry_runnable, 
    inquiry_tools,
    order_create_runnable, 
    order_create_related_tools, 
    order_create_tool, 
    order_change_runnable,
    order_change_related_tools,
    order_change_tool,
    order_cancel_runnable,
    order_cancel_related_tools,
    order_cancel_tool,   
    primary_assistant_runnable, primary_assistant_tools
    )


builder = StateGraph(State)
builder.add_node("fetch_user_info", user_info)
builder.add_conditional_edges("fetch_user_info", route_to_workflow)
builder.add_node("leave_skill", pop_dialog_state)
builder.add_edge("leave_skill", "primary_assistant")
#--------------------------------------------------------------------------------------------------------------------------------------
# order inquiry sub-graph
builder.add_node(
    "enter_order_inquiry",
    create_entry_node("Order Inqury Assistant", "order_inquiry"),
)
builder.add_node("order_inquiry", Assistant(order_inquiry_runnable))
builder.add_edge("enter_order_inquiry", "order_inquiry")
builder.add_conditional_edges("order_inquiry", route_order_inquiry)
builder.add_node(
    "inquiry_tools",
    create_tool_node_with_fallback(inquiry_tools),
)
builder.add_edge("inquiry_tools", END)
#--------------------------------------------------------------------------------------------------------------------------------------
# order create sub-graph
builder.add_node(
    "enter_order_create",
    create_entry_node("Order Create Assistant", "order_create"),
)
builder.add_node("order_create", Assistant(order_create_runnable))
builder.add_edge("enter_order_create", "order_create")
builder.add_conditional_edges("order_create", order_create_route)
builder.add_node(
    "order_create_related_tools",
    create_tool_node_with_fallback(order_create_related_tools)
    )
builder.add_conditional_edges("order_create_related_tools", order_create_related_tools_route)
builder.add_node(
    "order_create_tool",
    create_tool_node_with_fallback(order_create_tool)
    )
builder.add_edge("order_create_tool", "reset_state_without_messages")

builder.add_node("present_product_list", present_product_list)
builder.add_edge("present_product_list", END)

builder.add_node("request_order_confirmation", request_order_confirmation)
builder.add_edge("request_order_confirmation", END)

builder.add_node("reset_state_without_messages", reset_state_without_messages)
builder.add_edge("reset_state_without_messages", END)
#--------------------------------------------------------------------------------------------------------------------------------------
# order change sub-graph
builder.add_node(
    "enter_order_change",
    create_entry_node("Order Change Assistant", "order_change"),
)
builder.add_node("order_change", Assistant(order_change_runnable))
builder.add_edge("enter_order_change", "order_change")
builder.add_conditional_edges("order_change", order_change_route)
builder.add_node(
    "order_change_related_tools", create_tool_node_with_fallback(order_change_related_tools)
)
builder.add_conditional_edges("order_change_related_tools", order_change_related_tools_route)
builder.add_node(
    "order_change_tool", create_tool_node_with_fallback(order_change_tool)
)
builder.add_edge("order_change_tool", "reset_state_without_messages")

builder.add_node("display_user_order", display_user_order)
builder.add_edge("display_user_order", END)

builder.add_node("ask_how_to_change", ask_how_to_change)
builder.add_edge("ask_how_to_change", END)

builder.add_node("request_order_change_confirmation", request_order_change_confirmation)
builder.add_edge("request_order_change_confirmation", END)
#--------------------------------------------------------------------------------------------------------------------------------------
# order cancel sub-graph
builder.add_node(
    "enter_order_cancel",
    create_entry_node("Order Cancel Assistant", "order_cancel"),
)
builder.add_node("order_cancel", Assistant(order_cancel_runnable))
builder.add_edge("enter_order_cancel", "order_cancel")
builder.add_conditional_edges("order_cancel", order_cancel_route)
builder.add_node(
    "order_cancel_related_tools", create_tool_node_with_fallback(order_cancel_related_tools)
)
builder.add_conditional_edges("order_cancel_related_tools", order_cancel_related_tools_route)
builder.add_node(
    "order_cancel_tool", create_tool_node_with_fallback(order_cancel_tool)
)
builder.add_edge("order_cancel_tool", "reset_state_without_messages")

builder.add_node("request_order_cancel_confirmation", request_order_cancel_confirmation)
builder.add_edge("request_order_cancel_confirmation", END)
#--------------------------------------------------------------------------------------------------------------------------------------
# Primary assistant
builder.add_node("primary_assistant", Assistant(primary_assistant_runnable))
builder.add_node(
    "primary_assistant_tools", create_tool_node_with_fallback(primary_assistant_tools)
)
builder.add_edge("primary_assistant_tools", "primary_assistant")
builder.add_conditional_edges(
    "primary_assistant",
    route_primary_assistant,
    {
        "enter_order_inquiry": "enter_order_inquiry",
        "enter_order_create": "enter_order_create",
        "enter_order_change": "enter_order_change",
        "enter_order_cancel": "enter_order_cancel",
        "primary_assistant_tools": "primary_assistant_tools",
        END: END,
    },
)

builder.set_entry_point("fetch_user_info")

with SqliteSaver.from_conn_string(":memory:") as memory:
    orderbot_graph = builder.compile(
        checkpointer=memory,
        interrupt_before=["order_create_tool", "order_change_tool", "order_cancel_tool"]
    )