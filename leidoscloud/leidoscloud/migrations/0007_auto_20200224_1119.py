# Generated by Django 2.1.7 on 2020-02-24 11:19

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("leidoscloud", "0006_auto_20200224_1105"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockdata",
            name="time",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
