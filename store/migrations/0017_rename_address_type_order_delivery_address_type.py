# Generated by Django 5.1.3 on 2025-01-06 05:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0016_order_delivery_address_line_1_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='address_type',
            new_name='delivery_address_type',
        ),
    ]
