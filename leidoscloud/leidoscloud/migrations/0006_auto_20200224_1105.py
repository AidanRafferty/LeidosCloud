# Generated by Django 2.2.6 on 2020-02-24 11:05

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ("leidoscloud", "0005_auto_20200224_1037"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockdata",
            name="time",
            field=models.DateTimeField(
                default=datetime.datetime(2020, 2, 24, 11, 5, 11, 567530, tzinfo=utc)
            ),
        ),
    ]