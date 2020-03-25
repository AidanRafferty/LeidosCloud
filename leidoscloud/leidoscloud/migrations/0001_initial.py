# Generated by Django 2.2.6 on 2020-01-22 10:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="API",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=20)),
                ("long_name", models.CharField(max_length=30)),
                ("is_provider", models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name="Transition",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("start_time", models.DateTimeField(default=django.utils.timezone.now)),
                ("end_time", models.DateTimeField(null=True)),
                ("succeeded", models.BooleanField(default=False)),
                ("deleted", models.BooleanField(default=False)),
                (
                    "end_provider",
                    models.ForeignKey(
                        limit_choices_to={"is_provider": True},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="end_provider",
                        to="leidoscloud.API",
                    ),
                ),
                (
                    "start_provider",
                    models.ForeignKey(
                        limit_choices_to={"is_provider": True},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="start_provider",
                        to="leidoscloud.API",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Key",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=20)),
                ("value", models.CharField(max_length=100)),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="leidoscloud.API",
                    ),
                ),
            ],
        ),
    ]