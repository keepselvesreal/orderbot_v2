from typing import List, Optional
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import Runnable, RunnableLambda
from typing import Optional, Dict, Any


class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    messages: List[BaseMessage] = Field(default_factory=list)
    save_mode: Optional[str] = Field(default="both")  # "input", "output", "both"
    
    def add_messages(self, messages: List[BaseMessage]) -> None:
        """조건에 따라 메시지를 저장"""
        if self.save_mode == "input":
            input_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
            self.messages.extend(input_messages)
        elif self.save_mode == "output":
            output_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
            self.messages.extend(output_messages)
        elif self.save_mode == "both":
            self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

store = {}
def get_session_history(session_id: str, save_mode: str = "both") -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory(save_mode=save_mode)
    return store[session_id]

class RunnableWithMessageHistory(Runnable):
    def __init__(self, runnable: Runnable, get_session_history, input_messages_key: str, history_messages_key: str, context_key: Optional[str] = None):
        self.runnable = runnable
        self.get_session_history = get_session_history
        self.input_messages_key = input_messages_key
        self.history_messages_key = history_messages_key
        self.context_key = context_key
    
    def invoke(self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Any:
        session_id = config["configurable"]["session_id"]
        save_mode = config["configurable"].get("save_mode", "both")
        history = self.get_session_history(session_id, save_mode)
        
        current_input = input[self.input_messages_key]
        
        if isinstance(current_input, str):
            current_input_message = HumanMessage(content=current_input)
        
        input[self.history_messages_key] = history.messages
        
        result = self.runnable.invoke(input, config)
        
        if isinstance(result, AIMessage):
            if self.context_key and input.get(self.context_key):
                context = input[self.context_key]
                result_with_context = AIMessage(content=f"{context}\n{result.content}")
                history.add_messages([current_input_message, result_with_context])
            else:
                history.add_messages([current_input_message, result])
        
        return result

def add_memory(runnable, session_id, context="", save_mode="both"):
    runnable_with_memory = RunnableWithMessageHistory(
        runnable,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        context_key="context"
    )
    
    def memory_lambda(input):
        return runnable_with_memory.invoke(
            {**input, "context": context},
            config={"configurable": {"session_id": session_id, "save_mode": save_mode}}
        )
    
    memory_by_session = RunnableLambda(memory_lambda)
    
    return memory_by_session


def add_action_type(dict):
    inputs = dict["inputs"]
    action_type =  dict["action_type"]
    action_type = action_type.content
    # action_type = action_type.content
    inputs["action_type"] = action_type
    return inputs



