from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from django.db.models import Prefetch
from products.models import Order, OrderStatusChange

@tool
def get_recent_orders_by_status(user, status):
    """
    Retrieve the three most recent orders with a specific status for the given user.
    """

    recent_orders = Order.objects.filter(
        user=user,
        status_changes__status=status
    ).prefetch_related(
        Prefetch('status_changes', queryset=OrderStatusChange.objects.filter(status=status))
    ).order_by('-created_at')[:3]

    return recent_orders

tools = [get_recent_orders_by_status]

def determine_tool_usage(msg: AIMessage) -> Runnable:
    """Determine whether to use the tool based on the given condition."""
    print(msg)
    if msg.additional_kwargs: 
        tool_map = {tool.name: tool for tool in tools}
        tool_calls = msg.tool_calls.copy()
        for tool_call in tool_calls:
            tool_call["output"] = tool_map[tool_call["name"]].invoke(tool_call["args"])
        return tool_call["output"]
    else:
        return msg.content