# Generated by Django 5.1.3 on 2024-12-17 05:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0007_rename_product_type_product_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='discount_type',
        ),
        migrations.RemoveField(
            model_name='product',
            name='discount_value',
        ),
        migrations.RemoveField(
            model_name='product',
            name='is_discount_active',
        ),
        migrations.RemoveField(
            model_name='product',
            name='price',
        ),
    ]
