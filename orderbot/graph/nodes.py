from langchain_core.messages import ToolMessage

from .states import State
from .runnables import (
    present_product_list_runnable,
    request_order_confirmation_runnable,
    ask_order_runnable,
    ask_how_to_change_runnable,
    request_order_change_confirmation_runnable,
    request_order_cancel_confirmation_runnable
)
from .tools import (
    fetch_recent_order,
)


def user_info(state: State):
    print("-"*77)
    print("user_info 진입")


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


def present_product_list(state: State):
    print("-"*77)
    print("present_product_list 진입")
    print("state\n", state)

    messages = state["messages"]
    response = present_product_list_runnable.invoke({"messages": messages})
    response = response.content

    return {"messages": response} 


def request_order_confirmation(state: State):
    print("-"*77)
    print("request_order_confirmation 진입")
    print("state\n", state)

    messages = state["messages"]
    response = request_order_confirmation_runnable.invoke({"messages": messages})
    
    return {"messages": response}


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
                                        "orders": recent_orders})
    response = output.content
    print("response\n", response)

    return {"messages": response, "orders": recent_orders}


def ask_how_to_change(state: State):
    print("-"*77)
    print("ask_how_to_change 진입")
    print("state\n", state)

    messages = state["messages"]
    response = ask_how_to_change_runnable.invoke({"messages": messages})
    
    return {"messages": response}


def request_order_change_confirmation(state: State):
    print("-"*77)
    print("request_confirmation 진입")
    print("state\n", state)

    messages = state["messages"]
    response = request_order_change_confirmation_runnable.invoke({"messages": messages})
    
    return {"messages": response}


def request_order_cancel_confirmation(state: State):
    print("-"*77)
    print("request_order_cancel_confirmation 진입")
    print("state\n", state)

    messages = state["messages"]
    response = request_order_cancel_confirmation_runnable.invoke({"messages": messages})

    return {"messages": response}


def reset_state_without_messages(state: State):
    messages = state["messages"]
    sub_state = state.copy()
    sub_state.update({key: None for key in sub_state.keys() if key not in ["messages", "dialog_state"]})
    return {**sub_state, "messages": messages, "dialog_state": "pop"}