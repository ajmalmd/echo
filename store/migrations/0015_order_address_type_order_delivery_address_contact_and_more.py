# Generated by Django 5.1.3 on 2025-01-06 05:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0014_order_delivery_address_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='address_type',
            field=models.CharField(blank=True, choices=[('home', 'Home'), ('work', 'Work')], default=None, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_address_contact',
            field=models.CharField(blank=True, default=None, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_city',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_country',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_postal_code',
            field=models.CharField(blank=True, default=None, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_state',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
    ]
