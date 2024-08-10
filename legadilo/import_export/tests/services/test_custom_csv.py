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

import httpx
import pytest
import time_machine

from config import settings
from legadilo.feeds.models import Feed, FeedArticle, FeedCategory
from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedFactory
from legadilo.feeds.tests.fixtures import get_feed_fixture_content
from legadilo.import_export.services.custom_csv import import_custom_csv_file_sync
from legadilo.import_export.services.exceptions import DataImportError
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory
from legadilo.utils.testing import all_model_fields_except, serialize_for_snapshot


def test_import_invalid_custom_csv(user):
    with pytest.raises(DataImportError):
        import_custom_csv_file_sync(
            user, settings.APPS_DIR / "import_export/tests/fixtures/custom_csv/invalid_file.csv"
        )


@pytest.mark.django_db
def test_import_empty_file(user):
    nb_imported_articles, nb_imported_feeds, nb_imported_categories = import_custom_csv_file_sync(
        user, settings.APPS_DIR / "import_export/tests/fixtures/custom_csv/empty_file.csv"
    )

    assert nb_imported_articles == 0
    assert nb_imported_feeds == 0
    assert nb_imported_categories == 0
    assert Article.objects.count() == 0
    assert Feed.objects.count() == 0
    assert FeedCategory.objects.count() == 0


@pytest.mark.django_db
@time_machine.travel("2024-05-17 13:00:00", tick=False)
def test_import_custom_csv(user, httpx_mock, snapshot):
    feed_category = FeedCategoryFactory(
        user=user, title="Existing category", slug="existing-category"
    )
    FeedFactory(
        user=user,
        feed_url="https://example.com/existing.xml",
        category=feed_category,
        title="Existing feed",
    )
    ArticleFactory(
        user=user,
        title="Existing article",
        external_article_id="",
        link="https://example.com/article/existing",
        published_at="2024-05-17T13:00:00+00:00",
        updated_at="2024-05-17T13:00:00+00:00",
    )

    httpx_mock.add_response(
        url="https://example.com/rss2.xml",
        content=get_feed_fixture_content("sample_rss.xml"),
    )
    httpx_mock.add_response(
        url="https://example.com/rss4.xml",
        content=get_feed_fixture_content("sample_atom.xml"),
    )
    httpx_mock.add_exception(
        httpx.HTTPError("Failed to fetch"),
        url="https://example.com/rss8.xml",
    )

    nb_imported_articles, nb_imported_feeds, nb_imported_categories = import_custom_csv_file_sync(
        user, settings.APPS_DIR / "import_export/tests/fixtures/custom_csv/custom_csv.csv"
    )

    assert nb_imported_articles == 6
    assert nb_imported_feeds == 3
    assert nb_imported_categories == 2
    assert Article.objects.count() == 8
    assert Feed.objects.count() == 4
    assert FeedCategory.objects.count() == 3
    assert FeedArticle.objects.count() == 5

    snapshot.assert_match(
        serialize_for_snapshot(
            list(
                Article.objects.order_by("id").values(
                    *all_model_fields_except(
                        Article, {"id", "user", "obj_created_at", "obj_updated_at"}
                    )
                )
            )
        ),
        "articles.json",
    )
    snapshot.assert_match(
        serialize_for_snapshot(
            list(
                Feed.objects.order_by("id").values(
                    *all_model_fields_except(
                        Feed, {"id", "user", "category", "created_at", "updated_at"}
                    ),
                    "category__title",
                )
            )
        ),
        "feeds.json",
    )
    snapshot.assert_match(
        serialize_for_snapshot(
            list(
                FeedCategory.objects.order_by("id").values(
                    *all_model_fields_except(
                        FeedCategory, {"id", "user", "created_at", "updated_at"}
                    )
                )
            )
        ),
        "feed_categories.json",
    )
