import json 


def process_message(instance, message, data_from_client):
    if message == "show_products":
        instance.send_product_list()
        return True
    elif message == "get_all_orders":
        start_date = data_from_client.get("startDate")
        end_date = data_from_client.get("endDate")
        instance.get_all_orders(start_date, end_date)
        return True
    elif message == "get_order_by_status":
        order_status = data_from_client.get("orderStatus")
        start_date = data_from_client.get("startDate")
        end_date = data_from_client.get("endDate")
        instance.get_order_by_status(order_status, start_date, end_date)
        return True
    elif message == "create_order":
        user_id = data_from_client.get("userId")
        ordered_products = data_from_client.get("orderedProducts")
        instance.create_order(user_id, ordered_products)
        return True
    elif message == "order_to_change":
        order_change_type = "order_changed"
        start_date = data_from_client.get("startDate")
        end_date = data_from_client.get("endDate")
        instance.get_changeable_orders(order_change_type, start_date, end_date)
        return True
    elif message == "order_changed":
        order_id = data_from_client.get("orderId")
        instance.send_product_list(order_id)
        return True
    elif message == "change_order":
        order_id = data_from_client.get("orderId")
        ordered_products = data_from_client.get("orderedProducts")
        instance.change_order(order_id, ordered_products)
        return True
    elif message == "order_to_cancel":
        order_change_type = "order_canceled"
        start_date = data_from_client.get("startDate")
        end_date = data_from_client.get("endDate")
        instance.get_changeable_orders(order_change_type, start_date, end_date)
        return True
    elif message == "order_canceled":
        order_id = data_from_client.get("orderId")
        instance.cancel_order(order_id)
        return True
    return False


def execute_compiled_graph(compiled_graph, config, **kwargs):
    if kwargs == {}:
        kwargs = None
    output = compiled_graph.invoke(kwargs, config)
    return output
    

def dict_to_json(**kwargs):
    dict_data = kwargs
    json_data = json.dumps(dict_data, ensure_ascii=False)
    return json_data