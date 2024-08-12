from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages


def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """Push or pop the state."""
    if right is None:
        return left
    if right == "pop":
        return left[:-1]
    return left + [right]


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_info: str
    dialog_state: Annotated[
            list[
                Literal[
                    "order_inquiry",
                    "order_create",
                    "order_change",
                    "order_cancel",
                ]
            ],
            update_dialog_stack,
        ]
    order_id: int = None 
    orders: str = None
    selected_order: str = None
    product_presentation: bool = False
    request_order_change_message: bool = False
    request_approval_message: bool = False
    task_completed: bool = False