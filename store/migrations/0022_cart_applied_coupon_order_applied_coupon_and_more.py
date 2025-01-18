# Generated by Django 5.1.3 on 2025-01-18 08:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0015_remove_coupon_applied_to'),
        ('store', '0021_wallet_wallettransaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='applied_coupon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='manager.coupon'),
        ),
        migrations.AddField(
            model_name='order',
            name='applied_coupon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='manager.coupon'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='coupon_discount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
