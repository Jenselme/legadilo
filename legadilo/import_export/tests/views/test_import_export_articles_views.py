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
from io import BytesIO
from pathlib import Path

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.test import override_settings
from django.urls import reverse

from legadilo.feeds.models import Feed
from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedFactory
from legadilo.feeds.tests.fixtures import get_feed_fixture_content
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory
from legadilo.utils.testing import all_model_fields_except, serialize_for_snapshot
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


class TestImportExportArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("import_export:import_export_articles")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_import_unsupported_file(self, logged_in_sync_client):
        buffer = BytesIO(b"stuff")
        file = InMemoryUploadedFile(
            buffer,
            "some_file",
            "file.png",
            content_type="application/xml",
            size=100,
            charset="utf-8",
        )

        response = logged_in_sync_client.post(self.url, {"invalid_file": file})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="This file type is not supported for imports.",
            )
        ]


class TestImportCustomCSV:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("import_export:import_export_articles")

    def test_import_invalid_file(self, logged_in_sync_client):
        buffer = BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")
        file = InMemoryUploadedFile(
            buffer,
            "some_file",
            "file.png",
            content_type="application/xml",
            size=100,
            charset="utf-8",
        )

        response = logged_in_sync_client.post(
            self.url,
            {
                "csv_file": file,
            },
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "import_export/import_export_articles.html"
        assert response.context["form"].errors == {}
        assert Feed.objects.count() == 0
        assert Article.objects.count() == 0
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="The file you supplied is not valid.",
            )
        ]

    def test_import_in_memory_file(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_response(
            url="https://example.com/rss2.xml",
            content=get_feed_fixture_content("sample_rss.xml"),
        )
        httpx_mock.add_response(
            url="https://example.com/rss4.xml",
            content=get_feed_fixture_content("sample_atom.xml"),
        )

        with Path(
            settings.APPS_DIR / "import_export/tests/fixtures/custom_csv/custom_csv.csv"
        ).open("r", encoding="utf-8") as f:
            response = logged_in_sync_client.post(
                self.url,
                {
                    "csv_file": InMemoryUploadedFile(
                        f,
                        "some_file",
                        "file.png",
                        content_type="application/xml",
                        size=100,
                        charset="utf-8",
                    ),
                },
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "import_export/import_export_articles.html"
        assert response.context["form"].errors == {}
        assert Feed.objects.count() > 0
        assert Article.objects.count() > 0
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Successfully imported 4 feeds, 3 feed categories and 6 articles.",
            )
        ]

    @override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=0)
    def test_import_temporary_file(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_response(
            url="https://example.com/rss2.xml",
            content=get_feed_fixture_content("sample_rss.xml"),
        )
        httpx_mock.add_response(
            url="https://example.com/rss4.xml",
            content=get_feed_fixture_content("sample_atom.xml"),
        )
        temp_file = TemporaryUploadedFile(
            settings.APPS_DIR / "import_export/tests/fixtures/custom_csv/custom_csv.csv",  # type: ignore[arg-type]
            "text/csv",
            size=100,
            charset="utf-8",
        )
        with Path(
            settings.APPS_DIR / "import_export/tests/fixtures/custom_csv/custom_csv.csv"
        ).open("r", encoding="utf-8") as in_:
            Path(temp_file.file.name).write_text(in_.read(), encoding="utf-8")  # type: ignore[union-attr]

        response = logged_in_sync_client.post(
            self.url,
            {
                "csv_file": temp_file,
            },
        )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "import_export/import_export_articles.html"
        assert response.context["form"].errors == {}
        assert Feed.objects.count() > 0
        assert Article.objects.count() > 0
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Successfully imported 4 feeds, 3 feed categories and 6 articles.",
            )
        ]


class TestImportWallabag:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("import_export:import_export_articles")

    def test_import_invalid_data(self, logged_in_sync_client):
        buffer = BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")
        file = InMemoryUploadedFile(
            buffer,
            "some_file",
            "file.png",
            content_type="application/xml",
            size=100,
            charset="utf-8",
        )

        response = logged_in_sync_client.post(
            self.url,
            {
                "wallabag_file": file,
            },
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "import_export/import_export_articles.html"
        assert response.context["form"].errors == {}
        assert Feed.objects.count() == 0
        assert Article.objects.count() == 0
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="The file you supplied is not valid.",
            )
        ]

    def test_import_invalid_file(self, logged_in_sync_client):
        with Path(
            settings.APPS_DIR / "import_export/tests/fixtures/wallabag/invalid_wallabag.json"
        ).open("r", encoding="utf-8") as f:
            response = logged_in_sync_client.post(
                self.url,
                {
                    "wallabag_file": InMemoryUploadedFile(
                        f,
                        "some_file",
                        "file.png",
                        content_type="application/json",
                        size=100,
                        charset="utf-8",
                    ),
                },
            )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "import_export/import_export_articles.html"
        assert response.context["form"].errors == {}
        assert Feed.objects.count() == 0
        assert Article.objects.count() == 0
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="The file you supplied is not valid.",
            )
        ]

    def test_import_valid_file(self, logged_in_sync_client, snapshot):
        with Path(
            settings.APPS_DIR / "import_export/tests/fixtures/wallabag/valid_wallabag.json"
        ).open("r", encoding="utf-8") as f:
            response = logged_in_sync_client.post(
                self.url,
                {
                    "wallabag_file": InMemoryUploadedFile(
                        f,
                        "some_file",
                        "file.png",
                        content_type="application/json",
                        size=100,
                        charset="utf-8",
                    ),
                },
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "import_export/import_export_articles.html"
        assert response.context["form"].errors == {}
        assert Feed.objects.count() == 0
        assert Article.objects.count() > 0
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Successfully imported 1 articles",
            )
        ]
        snapshot.assert_match(
            serialize_for_snapshot(
                list(
                    Article.objects.order_by("link").values(
                        *all_model_fields_except(
                            Article, {"id", "user", "obj_created_at", "obj_updated_at"}
                        )
                    )
                )
            ),
            "walabag_articles.json",
        )
