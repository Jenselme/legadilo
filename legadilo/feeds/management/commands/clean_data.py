# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
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

from django.core.management import BaseCommand

from legadilo.feeds.models import Feed
from legadilo.reading.models import Article, ArticleFetchError


class Command(BaseCommand):
    def handle(self, *args, **options):
        Feed.objects.get_feed_update_for_cleanup().delete()
        ArticleFetchError.objects.get_queryset().for_cleanup().delete()
        Article.objects.get_queryset().for_cleanup().delete()