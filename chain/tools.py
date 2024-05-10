from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

@tool
def get_recent_orders_by_status(user, status):
    """
    Retrieve the three most recent orders with a specific status for the given user.
    """
    # status_changes 를 통해 필터링하고, 주문 생성 순으로 정렬한 다음 최대 3개의 주문을 반환합니다.
    return f"{status} 상태인 {user} 사용자의 최근 주문 3건!"

tools = [get_recent_orders_by_status]

def call_tools(msg: AIMessage) -> Runnable:
    """Simple sequential tool calling helper."""
    tool_map = {tool.name: tool for tool in tools}
    tool_calls = msg.tool_calls.copy()
    for tool_call in tool_calls:
        tool_call["output"] = tool_map[tool_call["name"]].invoke(tool_call["args"])
    return tool_calls