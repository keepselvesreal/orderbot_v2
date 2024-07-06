import json
import uuid

from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from langchain_core.messages import ToolMessage

from chain.langgraph_graphs import orderbot_graph


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
        order_id = text_data_json.get("orderId")
        orders = text_data_json.get("orders")
        selected_order = text_data_json.get("orderDetails")
        print("order_id: ", order_id)
        print("selected_order\n", selected_order)
        if order_id:
            orderbot_graph.update_state(config, {"order_id": order_id,
                                                 "selected_order": selected_order,
                                                 "orders": None})
            message = "요청한 작업을 수행할 주문은 아래와 같아."
        self.confirm_message = text_data_json.get("confirmMessage")
        print("self.confirm_message: ", self.confirm_message)
        self.tool_call_id = text_data_json.get("toolCallId")

        if "confirmMessage" not in text_data_json:
            output = orderbot_graph.invoke({"messages": ("user", message),
                                            "user_info": user_id},
                                            # "order_id": order_id,
                                            # "selected_order": selected_order}, 
                                            config)
            orders = output.get("orders")
        else:
            print("-"*70)
            print("승인 메시지 확인 구간 진입")
            if message == "y":
                print("승인 메시지 확인")
                output = orderbot_graph.invoke(
                    None,
                    config,
                )
                print()
            else:
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
        print("-"*70)
        print("model output\n", output)
        response = output["messages"][-1].content
        print("response\n", response)
        now = timezone.now()
        
        snapshot = orderbot_graph.get_state(config)
        # print("snapshot\n", snapshot)

        if snapshot.next:
            print("-"*70)
            print("snapshot.next 존재")
            print("output['messages'][-1]\n",  output["messages"][-1])
            self.confirmation_message = True
            self.tool_call_id = output["messages"][-1].tool_calls[0]["id"]
            response = "작업을 승인하시려면 y를 입력하시고, 거부하신다면 변경 사유를 알려주세요!"
            
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
            print("snapshot.next 존재 X")
            # self.send(text_data=json.dumps(
            #         {"user": self.user.username,
            #         "message": response,
            #         "datetime": now.isoformat(),
            #         },
            #         ensure_ascii=False
            #         ))
            if orders:
                print("orders 존재 시 처리 구간 진입")
                print("orders\n", orders)
                if order_id is None:
                    response = "지난 주문 내역은 아래와 같습니다."
                self.send(text_data=json.dumps(
                    {"user": self.user.username,
                    "message": response,
                    "datetime": now.isoformat(),
                    "recent_orders": orders, 
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
            