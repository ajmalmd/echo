# Generated by Django 5.1.3 on 2025-01-08 06:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0018_wishlist'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='razorpay_order_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='razorpay_payment_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='razorpay_payment_status',
            field=models.CharField(blank=True, choices=[('created', 'Created'), ('paid', 'Paid'), ('failed', 'Failed')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_payment',
            field=models.CharField(choices=[('cod', 'Cash on Delivery'), ('razorpay', 'Razorpay')], default='cod', max_length=20),
        ),
    ]
