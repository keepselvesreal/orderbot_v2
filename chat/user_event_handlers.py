import json
import uuid

from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from chain.langgraph_tools import fetch_product_list2
from products.models import Product, Order, OrderStatus



def send_product_list(instance, selected_order_id=None):
    from .utilities import dict_to_json
    print("-"*70)
    print("send_product_list 진입")

    products = fetch_product_list2()
    products = json.loads(products)

    if selected_order_id:
        message = "주문을 어떻게 변경하실 건가요?\n아래 메뉴 목록에서 새로 주문해주세요."
    else:
        message = "다음은 메뉴 목록입니다."

    json_data = dict_to_json(message=message, products=products, order_id=selected_order_id)
    instance.send(text_data=json_data)

def get_all_orders(instance, start_date=None, end_date=None):
    from .utilities import dict_to_json
    print("-"*70)
    print("get_all_orders 진입")
    print("startdate / enddate: ", f"{start_date} / {end_date}")

    orders = Order.objects.all()

    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])
    elif start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    elif end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    orders_data = [order.to_dict() for order in orders]

    json_data = dict_to_json(message="전체 주문 목록입니다.", fetched_orders=orders_data)
    instance.send(text_data=json_data)

def get_order_by_status(instance, order_status, start_date=None, end_date=None):
    from .utilities import dict_to_json
    print("-"*70)
    print("get_order_by_status 진입")
    print("startdate / enddate: ", f"{start_date} / {end_date}")

    orders = Order.objects.filter(order_status=order_status)

    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])
    elif start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    elif end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    orders_data = [order.to_dict() for order in orders]
    status_name = dict(OrderStatus.STATUS_CHOICES)[order_status]

    json_data = dict_to_json(
        message=f"{status_name}인 주문 목록입니다.",
        fetched_orders=orders_data
    )
    instance.send(text_data=json_data)

def get_changeable_orders(instance, order_change_type, start_date=None, end_date=None):
    from .utilities import dict_to_json
    print("-"*70)
    print("get_changeable_orders 진입")
    print("startdate / enddate: ", f"{start_date} / {end_date}")

    if order_change_type == "order_changed":
        message = "주문 변경이 가능한 주문 목록입니다."
    else:
        message = "주문 취소가 가능한 주문 목록입니다."

    orders = Order.objects.exclude(order_status="order_canceled")

    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])
    elif start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    elif end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    orders_data = [order.to_dict() for order in orders]

    json_data = dict_to_json(
        message=message,
        changeable_orders=orders_data,
        order_change_type=order_change_type
    )
    instance.send(text_data=json_data)

def create_order(instance, user_id, ordered_products):
    from .utilities import dict_to_json
    try:
        print("-"*70)
        print("create_order 진입")
        print("ordered_products\n", ordered_products)

        user = User.objects.get(id=user_id)

        with transaction.atomic():
            order = Order.objects.create(user=user)

            total_price = Decimal('0.00')
            for ordered_product in ordered_products:
                try:
                    product = Product.objects.get(product_name=ordered_product["productName"])
                except ObjectDoesNotExist:
                    json_data = dict_to_json(
                        message='error',
                        error=f'Product not found: {ordered_product["productName"]}'
                    )
                    instance.send(text_data=json_data)
                    return

                order.order_items.create(product=product, quantity=ordered_product["quantity"], price=Decimal(ordered_product["productPrice"]))
                total_price += Decimal(ordered_product["productPrice"]) * Decimal(ordered_product["quantity"])

            json_data = dict_to_json(
                message="order_confirmed",
                order_id=order.id,
                total_price=str(total_price)
            )
            instance.send(text_data=json_data)
    except ObjectDoesNotExist:
        json_data = dict_to_json(
            message='error',
            error='User not found'
        )
        instance.send(text_data=json_data)
    except Exception as e:
        json_data = dict_to_json(
            message='error',
            error=str(e)
        )
        instance.send(text_data=json_data)

def change_order(instance, order_id, ordered_products):
    from .utilities import dict_to_json
    try:
        print("-" * 70)
        print("change_order 진입")
        print("ordered_products\n", ordered_products)

        with transaction.atomic():
            try:
                order = Order.objects.get(id=order_id)
            except ObjectDoesNotExist:
                json_data = dict_to_json(
                    message='error',
                    error=f'Order not found: {order_id}'
                )
                instance.send(text_data=json_data)
                return

            order.order_status = 'order_changed'
            order.save()

            order.order_items.all().delete()

            total_price = Decimal('0.00')
            for ordered_product in ordered_products:
                try:
                    product = Product.objects.get(product_name=ordered_product["productName"])
                except ObjectDoesNotExist:
                    json_data = dict_to_json(
                        message='error',
                        error=f'Product not found: {ordered_product["productName"]}'
                    )
                    instance.send(text_data=json_data)
                    return

                order.order_items.create(product=product, quantity=ordered_product["quantity"], price=Decimal(ordered_product["productPrice"]))
                total_price += Decimal(ordered_product["productPrice"]) * Decimal(ordered_product["quantity"])

            json_data = dict_to_json(
                message='order_changed_confirmed',
                order_id=order.id,
                total_price=str(total_price)
            )
            instance.send(text_data=json_data)
    except ObjectDoesNotExist:
        json_data = dict_to_json(
            message='error',
            error='Order not found'
        )
        instance.send(text_data=json_data)
    except Exception as e:
        json_data = dict_to_json(
            message='error',
            error=str(e)
        )
        instance.send(text_data=json_data)

def cancel_order(instance, order_id):
    from .utilities import dict_to_json
    print("-"*70)
    print("cancel_order 진입")
    print("order_id: ", order_id)
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)

            order.order_status = 'order_canceled'
            order.save()

            order_status, created = OrderStatus.objects.get_or_create(
                order=order,
                status='order_canceled',
                defaults={'changed_at': timezone.now()}
            )

            if not created:
                print(f"주문 {order_id}에 대한 취소 기록이 이미 존재합니다.")

            json_data = dict_to_json(
                message=f"주문 {order_id}가 취소되었습니다.",
                order_status=order.order_status,
                order_id=order_id
            )
            instance.send(text_data=json_data)
    except Order.DoesNotExist:
        json_data = dict_to_json(
            message=f"주문 {order_id}를 찾을 수 없습니다."
        )
        instance.send(text_data=json_data)
    except Exception as e:
        json_data = dict_to_json(
            message=f"주문 취소 중 오류가 발생했습니다: {str(e)}"
        )
        instance.send(text_data=json_data)
