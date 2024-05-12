from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from django.contrib.auth.models import User
from django.db.models import Prefetch
from products.models import Order, OrderStatus

@tool
def get_recent_orders_by_status(user_id, status):
    """
    Retrieve the three most recent orders with a specific status for the given user.
    """

    user = User.objects.get(id=user_id)

    recent_orders = Order.objects.filter(
        user=user,
        order_status__status=status,
    ).prefetch_related(
        Prefetch('status_changes', queryset=OrderStatus.objects.filter(status=status))
    ).order_by('-created_at')[:3]

    print("recent_orders: ", recent_orders)
    return [order.to_dict() for order in recent_orders]  # 각 order 객체를 딕셔너리로 변환

tools = [get_recent_orders_by_status]

def determine_tool_usage(msg: AIMessage) -> Runnable:
    """Determine whether to use the tool based on the given condition."""
    print(msg)
    if msg.additional_kwargs: 
        tool_map = {tool.name: tool for tool in tools}
        tool_calls = msg.tool_calls.copy()
        for tool_call in tool_calls:
            tool_call["output"] = tool_map[tool_call["name"]].invoke(tool_call["args"])
        print("도구 출력 결과: ", tool_call["output"])
        return tool_call["output"]
    else:
        return msg.content