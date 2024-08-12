from django.contrib import admin
from .models import Product, Order, OrderItem, OrderStatus


class ProductOrderItemInline(admin.StackedInline):
    model = OrderItem
    extra = 1
    readonly_fields = ("order", "price")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'quantity', 'price']
    search_fields = ["product_name"]
    inlines = [ProductOrderItemInline]
    

class OrderItemInline(admin.StackedInline):
    model = OrderItem
    extra = 1  # 기본적으로 보여질 빈 폼의 수

class OrderStatusInline(admin.StackedInline):
    model = OrderStatus
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ["user__username"]
    inlines = [OrderItemInline, OrderStatusInline]


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'changed_at']
    list_filter = ['status', 'changed_at']
    search_fields = ["order__user__username"]