# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Generated by Django 5.2.4 on 2025-07-27 14:05
import logging

from django.db import connection, migrations, models

import legadilo.utils.time_utils
from legadilo.utils.pagination import paginate_qs

logger = logging.getLogger(__name__)


def fill_feed_article_id(apps, schema_editor):
    FeedArticle = apps.get_model("feeds", "FeedArticle")
    Article = apps.get_model("reading", "Article")
    for feed_article in paginate_qs(
        FeedArticle.objects.all().select_related("article").order_by("id")
    ):
        feed_article.feed_article_id = (
            feed_article.article.external_article_id or feed_article.article.url
        )
        feed_article.save(
            update_fields=[
                "feed_article_id",
            ]
        )

    # Handle duplicates to be able to create the unique index.
    # Keep only the most recent of the duplicates to have the most recent URL.
    # Since I'm the only one with articles in there, I know it's fine.
    feed_article_ids_to_delete = []
    article_ids_to_delete = []
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT
               (array_agg(feeds_feedarticle.id ORDER BY feeds_feedarticle.created_at DESC))[2:] AS feed_article_ids,
               (array_agg(feeds_feedarticle.article_id ORDER BY feeds_feedarticle.created_at DESC))[2:] AS article_ids
        FROM "feeds_feedarticle"
        GROUP BY feeds_feedarticle.feed_id, feeds_feedarticle.feed_article_id
        HAVING COUNT(DISTINCT "feeds_feedarticle"."article_id") > 1;
        """)
        for feed_article_ids, article_ids in cursor.fetchall():
            feed_article_ids_to_delete.extend(feed_article_ids)
            article_ids_to_delete.extend(article_ids)

    deletion_result = FeedArticle.objects.filter(id__in=feed_article_ids_to_delete).delete()
    logger.info("Deleted %s FeedArticle", deletion_result)
    deletion_result = Article.objects.filter(id__in=article_ids_to_delete).delete()
    logger.info("Deleted %s Article", deletion_result)


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0012_apply_cleaner_sanitization"),
        ("reading", "0013_apply_cleaner_sanitization"),
    ]

    operations = [
        migrations.AddField(
            model_name="feedarticle",
            name="feed_article_id",
            field=models.TextField(default=""),
        ),
        migrations.AddField(
            model_name="feedarticle",
            name="last_seen_at",
            field=models.DateTimeField(default=legadilo.utils.time_utils.utcnow),
        ),
        migrations.RunPython(fill_feed_article_id, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="feedarticle",
            constraint=models.UniqueConstraint(
                models.F("feed"),
                models.F("feed_article_id"),
                name="feeds_feedarticle_article_linked_once_per_feed_id",
            ),
        ),
        migrations.AlterField(
            model_name="feedarticle",
            name="feed_article_id",
            field=models.TextField(),
        ),
    ]
