from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda


store = {}
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def add_memory(runnable, session_id):
    runnable_with_memory = RunnableWithMessageHistory(
        runnable,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        )
    memory_by_session = RunnableLambda(
        lambda input: runnable_with_memory.invoke(input,
                                                  config={"configurable": {"session_id": session_id}}
                                                  )
                                                  )
    return memory_by_session


def add_action_type(dict):
    inputs = dict["inputs"]
    action_type =  dict["action_type"]
    action_type = action_type.content
    # action_type = action_type.content
    inputs["action_type"] = action_type
    return inputs



