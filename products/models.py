from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    product_name = models.CharField(max_length=255, null=False)
    quantity = models.IntegerField(null=False)
    price = models.IntegerField(null=False)

    def __str__(self):
        return f"{self.product_name} (기본 수량-{self.quantity}개, 기본 수량의 가격-{self.price}원)"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_status = models.ForeignKey('OrderStatus', on_delete=models.SET_NULL, null=True, related_name='orders')
    
    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "status": str(self.order_status) if self.order_status else None,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) 

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name} at {self.price} each"


class OrderStatus(models.Model):
    STATUS_CHOICES = (
        ('order', '주문 완료'),
        ('payment_completed', '입금 완료'),
        ('order_changed', '주문 변경'),
        ('order_canceled', '주문 취소'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_changes')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='order')
    changed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order {self.order.id} changed to {self.status} on {self.changed_at}"

