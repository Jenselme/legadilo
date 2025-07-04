# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# Generated by Django 5.0.6 on 2024-05-28 21:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArticleFetchError",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("message", models.TextField()),
                ("technical_debug_data", models.JSONField(blank=True, null=True)),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="article_fetch_errors",
                        to="reading.article",
                    ),
                ),
            ],
        ),
    ]
