import json
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
import os

from chain.chains import full_chain # chain_with_tools_n_history


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        print(self.user)
        self.accept()

    def disconnect(self):
        pass

    def receive(self, text_data):
        print(text_data)
        text_data_json = json.loads(text_data)
        user = text_data_json["user_id"]
        message = text_data_json["message"]
        response_message = self.orderbot_response(user, message)
        now = timezone.now()
        
        self.send(text_data=json.dumps(
            {"message": response_message, 
             "datetime": now.isoformat(),
             "user": self.user.username} # User Object인 듯
            ))
        
    def orderbot_response(self, user, message):
        # products.json 파일의 경로 설정
        current_directory = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(current_directory, '..', 'chain', 'files', 'products.json')

        # JSON 파일 읽어오기
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            products = json.load(json_file)

        try:
            response = full_chain.invoke(
                {"user_id": user, "input": message, "products": products},
                config={"configurable": {"session_id": "test_240514-3"}}
            )
            print("full chain 출력: ", response)
            response = response[0]
            print("response[0]: ", response, type(response))
            if isinstance(response, QuerySet):
                print("QuerySet 처리 구간 진입")
                print("response: ", response)
                response = [order.to_dict() for order in response]
            elif hasattr(response, "to_dict"):
                response = response.to_dict()
            response = json.dumps(response)
            print("json.dumps() 출력: ", response)
            # response = summary_chain.invoke(
            #     {"input": response}
            # ).content
            return response
        except ObjectDoesNotExist:
            return json.dumps({"error": "User or order not found"})
        except Exception as e:
            return json.dumps({"error": str(e)})
