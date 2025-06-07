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

import httpx
import pytest
from django.conf import settings

from legadilo.feeds.models import Feed, FeedArticle, FeedCategory
from legadilo.feeds.services.feed_parsing import FeedFileTooBigError
from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedFactory
from legadilo.feeds.tests.fixtures import get_feed_fixture_content
from legadilo.import_export.services.opml import import_opml_file_sync
from legadilo.reading.models import Article


@pytest.mark.django_db
@pytest.mark.parametrize(
    "file_name",
    [
        "empty.opml",
        "empty_no_body.opml",
        "empty_no_outline.opml",
    ],
)
def test_import_empty_files(user, file_name: str):
    nb_imported_feeds, nb_imported_categories = import_opml_file_sync(
        user, settings.APPS_DIR / "import_export/tests/fixtures/opml" / file_name
    )

    assert nb_imported_feeds == 0
    assert nb_imported_categories == 0
    assert FeedCategory.objects.count() == 0
    assert Feed.objects.count() == 0
    assert Article.objects.count() == 0


def test_import_valid_files(user, httpx_mock):
    httpx_mock.add_response(
        url="https://www.example.com/feeds/all.rss.xml",
        content=get_feed_fixture_content("sample_rss.xml"),
    )
    httpx_mock.add_response(
        url="https://www.example.eu/feeds/all.atom.xml",
        content=get_feed_fixture_content("sample_atom.xml"),
    )

    nb_imported_feeds, nb_imported_categories = import_opml_file_sync(
        user, settings.APPS_DIR / "import_export/tests/fixtures/opml/valid.opml"
    )

    assert nb_imported_feeds == 2
    assert nb_imported_categories == 1
    assert FeedCategory.objects.count() == 1
    category = FeedCategory.objects.get()
    assert category.user == user
    assert category.title == "Category 1"
    assert category.slug == "category-1"
    assert Feed.objects.count() == 2
    assert sorted(Feed.objects.values_list("feed_url", "site_url")) == [
        ("https://www.example.com/feeds/all.rss.xml", "http://example.org/"),
        ("https://www.example.eu/feeds/all.atom.xml", "http://example.org/"),
    ]
    assert Article.objects.count() == 2
    assert FeedArticle.objects.count() == 3


def test_import_valid_files_some_data_already_exist(user, httpx_mock):
    httpx_mock.add_response(
        url="https://www.example.com/feeds/all.rss.xml",
        content=get_feed_fixture_content("sample_rss.xml"),
    )
    httpx_mock.add_response(
        url="https://www.example.eu/feeds/all.atom.xml",
        content=get_feed_fixture_content("sample_atom.xml"),
    )
    FeedFactory(user=user, feed_url="https://www.example.com/feeds/all.rss.xml")
    FeedCategoryFactory(user=user, title="Category 1", slug="category-1")

    nb_imported_feeds, nb_imported_categories = import_opml_file_sync(
        user, settings.APPS_DIR / "import_export/tests/fixtures/opml/valid.opml"
    )

    assert nb_imported_feeds == 1
    assert nb_imported_categories == 0
    assert FeedCategory.objects.count() == 1
    category = FeedCategory.objects.get()
    assert category.user == user
    assert category.title == "Category 1"
    assert category.slug == "category-1"
    assert Feed.objects.count() == 2
    assert set(Feed.objects.values_list("feed_url", "site_url")) == {
        ("https://www.example.eu/feeds/all.atom.xml", "http://example.org/"),
        ("https://www.example.com/feeds/all.rss.xml", "https://example.com"),
    }
    assert Article.objects.count() == 2
    assert FeedArticle.objects.count() == 2


def test_import_valid_files_with_network_errors(user, httpx_mock):
    httpx_mock.add_exception(
        httpx.HTTPError("Failed to fetch"),
        url="https://www.example.com/feeds/all.rss.xml",
    )
    httpx_mock.add_exception(
        FeedFileTooBigError,
        url="https://www.example.eu/feeds/all.atom.xml",
    )

    nb_imported_feeds, nb_imported_categories = import_opml_file_sync(
        user, settings.APPS_DIR / "import_export/tests/fixtures/opml/valid.opml"
    )

    assert nb_imported_feeds == 1
    assert nb_imported_categories == 1
    assert FeedCategory.objects.count() == 1
    category = FeedCategory.objects.get()
    assert category.user == user
    assert category.title == "Category 1"
    assert category.slug == "category-1"
    assert Feed.objects.count() == 1
    assert list(Feed.objects.values_list("feed_url", "site_url", "enabled")) == [
        ("https://www.example.com/feeds/all.rss.xml", "https://www.example.com/", False),
    ]
    assert Article.objects.count() == 0
    assert FeedArticle.objects.count() == 0
