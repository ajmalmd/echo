# Generated by Django 5.1.3 on 2024-12-06 13:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0003_rename_name_productvariant_color'),
    ]

    operations = [
        migrations.RenameField(
            model_name='productvariant',
            old_name='color',
            new_name='name',
        ),
    ]
