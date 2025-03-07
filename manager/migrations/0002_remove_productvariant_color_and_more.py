# Generated by Django 5.1.3 on 2024-12-06 13:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productvariant',
            name='color',
        ),
        migrations.AlterField(
            model_name='product',
            name='connectivity',
            field=models.CharField(choices=[('true_wireless', 'True Wireless'), ('wired', 'Wired'), ('wireless', 'Wireless'), ('multi', 'Multi-functional')], max_length=20),
        ),
        migrations.AlterField(
            model_name='product',
            name='type',
            field=models.CharField(choices=[('in_ear', 'In the Ear'), ('over_ear', 'Over the Ear')], max_length=20),
        ),
    ]
