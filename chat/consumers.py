import json

from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from langchain_core.messages import ToolMessage

from chain.langgraph_graphs import orderbot_graph
from chain.langgraph_utilities import extract_message_from_event

import uuid
thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        # Todo: user_id로 대체 
        "passenger_id": "1089",
        # Checkpoints are accessed by thread_id
        "thread_id": thread_id,
    }
}

class ChatConsumer(WebsocketConsumer):
    SESSION_ID = "240606"

    def connect(self):
        self.user = self.scope["user"]
        self.confirmation_message = None
        self.tool_call_id = None
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        print("-"*70)
        print("receive 진입")
        print("클라이언트가 보낸 데이터\n", text_data)

        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        user_id = text_data_json["userId"]
        self.confirm_message = text_data_json.get("confirmMessage")
        self.tool_call_id = text_data_json.get("toolCallId")

        if "confirmMessage" not in text_data_json:
            output = orderbot_graph.invoke({"messages": ("user", message),
                                            "user_info": user_id}, 
                                            config, stream_mode="values")
            # response = output["messages"][-1].content
        else:
            print("승인 메시지 확인 구간 진입")
            if message == "y":
                print("승인 메시지 확인")
                # Just continue
                output = orderbot_graph.invoke(
                    None,
                    config,
                )
                print()
            else:
                # Satisfy the tool invocation by
                # providing instructions on the requested changes / change of mind
                output = orderbot_graph.invoke(
                    {
                        "messages": [
                            ToolMessage(
                                tool_call_id=self.tool_call_id,
                                content=f"API call denied by user. Reasoning: '{message}'. Cㄴontinue assisting, accounting for the user's input.",
                            )
                        ]
                    },
                    config,
                )
        response = output["messages"][-1].content
        snapshot = orderbot_graph.get_state(config)
        # print("snapshot\n", snapshot)

        now = timezone.now()
        if snapshot.next:
            print("snapshot.next 존재")
            self.confirmation_message = True
            self.tool_call_id = output["messages"][-1].tool_calls[0]["id"]
            response = "작업을 승인하시려면 y를 입력하시고, 아니라면 변경 사유를 알려주세요!"
            self.send(text_data=json.dumps(
            {"user": self.user.username,
             "message": response,
             "datetime": now.isoformat(),
             "confirm_message": self.confirmation_message,
             "tool_call_id": self.tool_call_id,
             },
             ensure_ascii=False
             ))
        else:
            self.send(text_data=json.dumps(
                {"user": self.user.username,
                "message": response,
                "datetime": now.isoformat(),
                },
                ensure_ascii=False
                ))