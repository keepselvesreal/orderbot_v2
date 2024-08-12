from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, OrderStatus

@receiver(post_save, sender=Order)
def create_or_update_order_status(sender, instance, created, **kwargs):
    OrderStatus.objects.update_or_create(
        order=instance,
        defaults={'status': instance.order_status}
    )