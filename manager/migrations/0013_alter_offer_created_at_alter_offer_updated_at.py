# Generated by Django 5.1.3 on 2025-01-14 07:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0012_alter_offer_brand_alter_offer_product'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offer',
            name='created_at',
            field=models.DateField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='offer',
            name='updated_at',
            field=models.DateField(auto_now=True),
        ),
    ]
