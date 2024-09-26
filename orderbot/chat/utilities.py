import json 

from .user_event_handlers import (
    send_product_list, 
    get_all_orders, 
    get_order_by_status,
    get_changeable_orders, 
    create_order, 
    change_order,
    cancel_order
)


def process_message(instance, message, data_from_client):
    if message == "show_products":
        send_product_list(instance)
        return True
    elif message == "get_all_orders":
        start_date = data_from_client.get("startDate")
        end_date = data_from_client.get("endDate")
        get_all_orders(instance, start_date, end_date)
        return True
    elif message == "get_order_by_status":
        order_status = data_from_client.get("orderStatus")
        start_date = data_from_client.get("startDate")
        end_date = data_from_client.get("endDate")
        get_order_by_status(instance, order_status, start_date, end_date)
        return True
    elif message == "create_order":
        ordered_products = data_from_client.get("orderedProducts")
        create_order(instance, ordered_products)
        return True
    elif message == "order_to_change":
        order_change_type = "order_changed"
        start_date = data_from_client.get("startDate")
        end_date = data_from_client.get("endDate")
        get_changeable_orders(instance, order_change_type, start_date, end_date)
        return True
    elif message == "order_changed":
        order_id = data_from_client.get("orderId")
        send_product_list(instance, order_id)
        return True
    elif message == "change_order":
        order_id = data_from_client.get("orderId")
        ordered_products = data_from_client.get("orderedProducts")
        change_order(instance, order_id, ordered_products)
        return True
    elif message == "order_to_cancel":
        order_change_type = "order_canceled"
        start_date = data_from_client.get("startDate")
        end_date = data_from_client.get("endDate")
        get_changeable_orders(instance, order_change_type, start_date, end_date)
        return True
    elif message == "order_canceled":
        order_id = data_from_client.get("orderId")
        cancel_order(instance, order_id)
        return True
    return False


def execute_compiled_graph(compiled_graph, config, **kwargs):
    if kwargs == {}:
        kwargs = None
    output = compiled_graph.invoke(kwargs, config)
    return output
    

def dict_to_json(**kwargs):
    dict_data = kwargs
    print(f"Dict Data: {dict_data}")  # 디버깅을 위해 추가
    json_data = json.dumps(dict_data, ensure_ascii=False)
    return json_data