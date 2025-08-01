# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# Generated by Django 5.0.6 on 2024-05-28 19:27

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0002_initial"),
        ("reading", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="feed",
            name="feeds_feed_disabled_reason_empty_when_enabled",
        ),
        migrations.AddField(
            model_name="feed",
            name="disabled_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddConstraint(
            model_name="feed",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("disabled_at__isnull", True), ("disabled_reason", ""), ("enabled", True)
                    ),
                    ("enabled", False),
                    _connector="OR",
                ),
                name="feeds_feed_disabled_reason_disabled_at_empty_when_enabled",
            ),
        ),
    ]
