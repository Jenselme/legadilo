# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.core.management import BaseCommand

from legadilo.feeds.models import FeedUpdate
from legadilo.reading.models import Article, ArticleFetchError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Clean data from database: old feed updates, article fetch errors and articles whose "
        "retention dates are passed"
    )

    def handle(self, *args, **options):
        deletion_result = FeedUpdate.objects.cleanup()
        logger.info("Deleted %s feed updates.", deletion_result)
        deletion_result = ArticleFetchError.objects.cleanup_article_fetch_errors()
        logger.info("Deleted %s article fetch errors.", deletion_result)
        deletion_result = Article.objects.cleanup_articles()
        logger.info("Deleted %s articles.", deletion_result)
