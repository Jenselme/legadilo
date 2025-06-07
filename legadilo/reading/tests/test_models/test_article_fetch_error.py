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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
import time_machine

from legadilo.reading.models import ArticleFetchError
from legadilo.reading.tests.factories import ArticleFetchErrorFactory


@pytest.mark.django_db
class TestArticleFetchErrorQuerySet:
    def test_for_cleanup(self):
        with time_machine.travel("2024-03-15 12:00:00"):
            object_to_cleanup = ArticleFetchErrorFactory()
        with time_machine.travel("2024-05-01 12:00:00"):
            ArticleFetchErrorFactory()

        with time_machine.travel("2024-06-01 12:00:00"):
            article_fetch_errors = ArticleFetchError.objects.get_queryset().for_cleanup()

        assert list(article_fetch_errors) == [object_to_cleanup]


@pytest.mark.django_db
class TestArticleFetchErrorManager:
    def test_cleanup_article_fetch_errors(self):
        with time_machine.travel("2024-03-15 12:00:00"):
            ArticleFetchErrorFactory()
        with time_machine.travel("2024-05-01 12:00:00"):
            object_to_keep = ArticleFetchErrorFactory()

        with time_machine.travel("2024-06-01 12:00:00"):
            deletion_result = ArticleFetchError.objects.cleanup_article_fetch_errors()

        assert deletion_result == (1, {"reading.ArticleFetchError": 1})
        assert list(ArticleFetchError.objects.all()) == [object_to_keep]
