# Generated by Django 5.1.3 on 2025-01-02 06:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_alter_orderitem_product_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_payment',
            field=models.CharField(choices=[('cod', 'Cash on Delivery')], default='cod', max_length=20),
        ),
    ]
