# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from django.core.management import BaseCommand

from legadilo.feeds.models import Feed, FeedDeletedArticle
from legadilo.reading.models import ArticleFetchError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Clean data from database: old feed updates, article fetch errors and articles whose "
        "retention dates are passed"
    )

    def handle(self, *args, **options):
        nb_deleted = Feed.objects.get_feed_update_for_cleanup().delete()
        logger.info("Deleted %s feed updates.", nb_deleted)
        nb_deleted = ArticleFetchError.objects.get_queryset().for_cleanup().delete()
        logger.info("Deleted %s article fetch errors.", nb_deleted)
        nb_deleted = FeedDeletedArticle.objects.cleanup_articles()
        logger.info("Deleted %s articles.", nb_deleted)
