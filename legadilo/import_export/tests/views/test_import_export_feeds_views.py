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
import time_machine
from django.urls import reverse

from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedFactory


@pytest.mark.django_db()
class TestExportFeeds:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("import_export:export_feeds")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_export_no_feed(self, snapshot, logged_in_sync_client):
        with time_machine.travel("2024-06-20 22:00:00", tick=False):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.headers.get("Content-Type") == "text/x-opml"
        snapshot.assert_match(response.content, "feeds.opml")

    def test_export(self, snapshot, logged_in_sync_client, user):
        category = FeedCategoryFactory(user=user, title="My Category")
        FeedFactory(title="Feed other user", feed_url="https://example.com/feeds/1.xml")
        FeedFactory(
            user=user,
            title="Feed without a category",
            feed_url="https://example.com/feeds/no_cat.xml",
        )
        FeedFactory(
            user=user,
            category=category,
            title="Feed with category",
            feed_url="https://example.com/feeds/2.xml",
        )

        with time_machine.travel("2024-06-20 22:00:00", tick=False):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.headers.get("Content-Type") == "text/x-opml"
        snapshot.assert_match(response.content, "feeds.opml")
