# Generated by Django 5.0 on 2023-12-31 12:14

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0003_feedupdate"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="feed",
            name="disabled_reason",
            field=models.CharField(default=""),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="feed",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("disabled_reason", ""), ("enabled", True)), ("enabled", False), _connector="OR"
                ),
                name="feeds_Feed_disabled_reason_empty_when_enabled",
            ),
        ),
    ]