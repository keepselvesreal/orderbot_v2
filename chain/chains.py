from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from .tools import tools, call_tools

from dotenv import load_dotenv
load_dotenv()


model = ChatOpenAI()

base_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "너는 뛰어나고 유능한 주문봇이야"
            "이전 대화와 현재 고객이 입력한 메시지 모두를 꼼꼼히 파악하여 답변해줘."
        ),
        ("human", "{input}"),

    ]
)

base_chain = base_prompt | model


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "너는 뛰어나고 유능한 주문봇이야"
            "이전 대화와 현재 고객이 입력한 메시지 모두를 꼼꼼히 파악하여 답변해줘."
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),

    ]
)

model = ChatOpenAI()

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

runnable_with_tools = prompt | model.bind_tools(tools)

with_message_history = RunnableWithMessageHistory(
    runnable_with_tools,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

chain_with_message_n_tools = with_message_history | call_tools