import json
import uuid

from channels.generic.websocket import WebsocketConsumer
from langchain_core.messages import HumanMessage, ToolMessage

from graph.graphs import orderbot_graph
from .utilities import process_message, execute_compiled_graph, dict_to_json


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
        print("*"*77)
        print("connect")
        print(f"sefl.scope: {self.scope}")
        self.user = self.scope["user"]
        print("self.user: ", self.user)
        
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        print("-"*70)
        print("receive 진입")
        print("클라이언트가 보낸 데이터\n", text_data)

        # text_data_json = json.loads(text_data)
        data_from_client = json.loads(text_data)
        print("data from client\n", data_from_client)
        message = data_from_client["message"]
        selected_order_id = data_from_client.get("orderId")
        selected_order = data_from_client.get("orderDetails")
        has_confirmation = data_from_client.get("confirmMessage")
        tool_call_id = data_from_client.get("toolCallId")
        user_id = data_from_client.get("userId") # 임시로
        
        is_precessed = process_message(self, message, data_from_client)
        if is_precessed: return

        print("selected_order_id: ", selected_order_id)
        print("selected_order\n", selected_order)
        # 브라우저에서 주문 아이디 선택한 경우
        if selected_order_id:
            orderbot_graph.update_state(config, {"orders": None})
            message = f"selected_order: {selected_order}"

        # 사용자 확인 필요한 도구 사용 여부 확인 위한 플래그 변수
        if has_confirmation is None:
            message_object = HumanMessage(content=message)
            # message_object = ("user", message)
            output = execute_compiled_graph(
                compiled_graph=orderbot_graph, 
                config=config, 
                messages=message_object, 
                user_info=user_id
                )
        else:
            # 사용자 확인 필요한 도구 사용할 때의 출력
            print("-"*70)
            print("승인 메시지 확인 구간 진입")
            if message == "y":
                # 도구 사용 승인 했을 때의 출력
                print("승인 메시지 확인")
                output = execute_compiled_graph(compiled_graph=orderbot_graph, config=config)
            else:
                # 도구 사용 승인하지 않았을 때의 출력
                message_object = ToolMessage(
                    content=f"API call denied by user. Reasoning: '{message}'. Continue assisting, accounting for the user's input.",
                    tool_call_id=tool_call_id,
                )
                output = execute_compiled_graph(
                    config=config,
                    message=message_object
                )
                
        print("-"*70)
        print("model output\n", output)
        response = output["messages"][-1].content
        print("response\n", response)
        order_history = output.get("orders")

        snapshot = orderbot_graph.get_state(config)

        # 사용자 확인 필요한 도구 사용 경우
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
        # 사용자 확인 필요한 도구 사용하지 않는 경우
        else:
            print("snapshot.next 존재 X")
            # 사용자 주문 내역이 조회된 경우
            if order_history:
                print("order_history 존재 시 처리 구간 진입")
                print("order_history\n", order_history)
                # 주문 선택하지 않은 경우. 반면 order_id 있다면 특정 주문 선택한 경우이고, 이때 response는 이를 바탕으로 어떤 처리 진행하고 model이 응답 생성한 경우.
                if selected_order_id is None:
                    response = "지난 주문 내역은 아래와 같습니다."
                json_data = dict_to_json(message=response, recent_orders=order_history)
                self.send(text_data=json_data)
            else:
                json_data = dict_to_json(message=response)
                self.send(text_data=json_data)
