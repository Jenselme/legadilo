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

from http import HTTPStatus

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse

from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedFactory
from legadilo.reading.tests.factories import ArticleFactory
from legadilo.utils.time import utcdt


class TestExportArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("import_export:export_articles")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_export_no_data(self, logged_in_sync_client, snapshot):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.headers["Content-Type"] == "text/csv"
        snapshot.assert_match(async_to_sync(self._get_content)(response), "no_content.csv")

    def test_export_some_content(self, logged_in_sync_client, user, snapshot):
        FeedCategoryFactory(user=user, id=1, title="Some category")
        FeedFactory(user=user, id=1, title="Some feed", feed_url="https://example.com/feeds/0.xml")
        ArticleFactory(
            user=user,
            id=1,
            title="Some article",
            link="https://example.com/article/0",
            published_at=utcdt(2024, 6, 23, 12, 0, 0),
            updated_at=utcdt(2024, 6, 23, 12, 0, 0),
        )

        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.headers["Content-Type"] == "text/csv"
        snapshot.assert_match(async_to_sync(self._get_content)(response), "export_all.csv")

    async def _get_content(self, response):
        content = b""
        async for partial_content in response.streaming_content:
            # Correct line ending because we will loose the initial one with git.
            content += partial_content.replace(b"\r\n", b"\n")

        return content
