import json
import uuid

from channels.generic.websocket import WebsocketConsumer
from langchain_core.messages import HumanMessage, ToolMessage

from graph.graphs import orderbot_graph
from .utilities import process_message, execute_compiled_graph, dict_to_json


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        if not hasattr(self, 'thread_id'):
            self.thread_id = str(uuid.uuid4())
        self.config = {
            "configurable": {
                "user": self.user.username,
                "thread_id": self.thread_id,
            }
        }

        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        data_from_client = json.loads(text_data)
        message = data_from_client["message"]
        selected_order_id = data_from_client.get("orderId")
        selected_order = data_from_client.get("orderDetails")
        has_confirmation = data_from_client.get("confirmMessage")
        tool_call_id = data_from_client.get("toolCallId")
        
        is_precessed = process_message(self, message, data_from_client)
        if is_precessed: return

        # 브라우저에서 사용자가 지난 주문 내역 중 특정 주문을 선택한 경우
        if selected_order_id:
            orderbot_graph.update_state(self.config, {"orders": None})
            message = f"selected_order: {selected_order}"

        # 사용자 승인이 필요한 도구를 에이전트가 선택했는지 확인하기 위한 플래그 변수
        if has_confirmation is None:
            message_object = HumanMessage(content=message)
            # message_object = ("user", message)
            output = execute_compiled_graph(
                compiled_graph=orderbot_graph, 
                config=self.config, 
                messages=message_object, 
                user_info=self.user.id
                )
        else:
            # 사용자 승인을 요청하는 도구를 에이전트가 선택한 경우
            print("-"*70)
            print("승인 메시지 확인 구간 진입")

            # 사용자가 도구 사용을 승인한 경우
            if message == "y":
                
                print("승인 메시지 확인")
                output = execute_compiled_graph(compiled_graph=orderbot_graph, config=self.config)
            else:
                message_object = ToolMessage(
                    content=f"API call denied by user. Reasoning: '{message}'. Continue assisting, accounting for the user's input.",
                    tool_call_id=tool_call_id,
                )
                output = execute_compiled_graph(
                    config=self.config,
                    message=message_object
                )
                
        response = output["messages"][-1].content
        order_history = output.get("orders")
        print("-"*70)
        print("model output\n", output)
        print("response\n", response)

        snapshot = orderbot_graph.get_state(self.config)

        # 사용자 승인을 요청하는 도구 사용이 필요한 경우
        if snapshot.next:
            print("-"*70)
            print("snapshot.next 존재")
            print("output['messages'][-1]\n",  output["messages"][-1])
           
            has_confirmation = True
            tool_call_id = output["messages"][-1].tool_calls[0]["id"]
            response = "작업을 승인하시려면 y를 입력하시고, 거부하신다면 변경 사유를 알려주세요!"
            
            json_data = dict_to_json(
                message=response,
                confirm_message=has_confirmation,
                tool_call_id=tool_call_id
                )
            self.send(text_data=json_data)
        else:
            print("snapshot.next 존재 X")

            # 사용자의 지난 주문 내역이 조회된 경우
            if order_history:
                print("order_history 존재 시 처리 구간 진입")
                print("order_history\n", order_history)
                
                # 지난 주문 내역 중 특정 주문을 선택하지 않은 경우. 
                # 특정 주문을 선택했다면, 이때의 response는 모델이 해당 주문으로 어떤 처리를 진행하고 생성한 응답.
                if selected_order_id is None:
                    response = "지난 주문 내역은 아래와 같습니다."
                json_data = dict_to_json(message=response, recent_orders=order_history)
                self.send(text_data=json_data)
            else:
                json_data = dict_to_json(message=response)
                self.send(text_data=json_data)
