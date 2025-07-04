# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# Generated by Django 5.1.2 on 2024-10-12 16:04

import django.db.models.deletion
from django.db import migrations, models

import legadilo.utils.validators


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0008_feed_article_retention_time"),
        ("reading", "0007_article_table_of_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="feedupdate",
            name="ignored_article_links",
            field=models.JSONField(
                blank=True,
                default=list,
                validators=[legadilo.utils.validators.list_of_strings_validator],
            ),
        ),
        migrations.AlterField(
            model_name="feedarticle",
            name="article",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="feed_articles",
                to="reading.article",
            ),
        ),
        migrations.CreateModel(
            name="FeedDeletedArticle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("article_link", models.URLField(max_length=1024)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "feed",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deleted_articles",
                        to="feeds.feed",
                    ),
                ),
            ],
            options={
                "db_table_comment": "Maintain a list of deleted article links from a feed so we don't add it again on next update.",
                "constraints": [
                    models.UniqueConstraint(
                        models.F("article_link"),
                        models.F("feed"),
                        name="feeds_feeddeletedarticle_delete_article_once_per_feed",
                    )
                ],
            },
        ),
    ]
