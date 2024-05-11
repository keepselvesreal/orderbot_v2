# Generated by Django 4.1.13 on 2024-05-11 07:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_alter_orderstatuschange_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderstatuschange',
            name='status',
            field=models.CharField(choices=[('order', '주문 완료'), ('payment_completed', '입금 완료'), ('order_changed', '주문 변경'), ('order_canceled', '주문 취소')], max_length=50),
        ),
    ]