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

from http import HTTPStatus

import httpx
import pytest
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag
from legadilo.reading.tests.factories import ArticleFactory, TagFactory
from legadilo.reading.tests.fixtures import get_article_fixture_content
from legadilo.utils.time_utils import utcdt, utcnow


@pytest.mark.django_db
class TestAddArticle:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("reading:add_article")
        self.article_url = "https://www.example.com/posts/en/1-super-article/"
        self.article_content = get_article_fixture_content("sample_blog_article.html")
        self.existing_tag = TagFactory(title="Existing tag", user=user)
        self.sample_payload = {"url": self.article_url}
        self.payload_with_tags = {
            "url": self.article_url,
            "tags": [self.existing_tag.slug, "New", "Tag with spaces"],
        }

    def test_access_if_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_get_form(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/add_article.html"

    def test_add_article(self, django_assert_num_queries, logged_in_sync_client, httpx_mock):
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        with django_assert_num_queries(14):
            response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "reading/add_article.html"
        messages = list(get_messages(response.wsgi_request))
        article = Article.objects.get()
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message=f'Article \'<a href="/reading/articles/{article.id}-on-the-3-musketeers/">'
                f"On the 3 musketeers</a>' successfully added!",
            )
        ]
        assert Article.objects.count() == 1
        assert list(article.tags.all()) == []

    def test_add_article_with_tags(
        self, django_assert_num_queries, logged_in_sync_client, httpx_mock
    ):
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        with django_assert_num_queries(18):
            response = logged_in_sync_client.post(self.url, self.payload_with_tags)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "reading/add_article.html"
        messages = list(get_messages(response.wsgi_request))
        article = Article.objects.get()
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message=f'Article \'<a href="/reading/articles/{article.id}-on-the-3-musketeers/">'
                f"On the 3 musketeers</a>' successfully added!",
            )
        ]
        assert Article.objects.count() == 1
        assert list(article.article_tags.values_list("tag__slug", "tagging_reason")) == [
            ("existing-tag", constants.TaggingReason.ADDED_MANUALLY),
            ("new", constants.TaggingReason.ADDED_MANUALLY),
            ("tag-with-spaces", constants.TaggingReason.ADDED_MANUALLY),
        ]

    def test_add_article_with_tags_other_user(
        self, user, other_user, logged_in_other_user_sync_client, httpx_mock
    ):
        ArticleFactory(user=user, link=self.article_url)
        TagFactory(user=other_user, title=self.existing_tag.title, slug=self.existing_tag.slug)
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        response = logged_in_other_user_sync_client.post(self.url, self.payload_with_tags)

        assert response.status_code == HTTPStatus.CREATED
        article = Article.objects.exclude(user=user).first()
        assert article is not None
        assert article.user == other_user
        assert article.tags.count() == 3
        assert set(article.tags.values_list("user_id", flat=True)) == {other_user.id}

    def test_add_article_no_content(self, logged_in_sync_client, httpx_mock, mocker):
        httpx_mock.add_response(text=self.article_content, url=self.article_url)
        mocker.patch("legadilo.reading.services.article_fetching._get_content", return_value="")

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "reading/add_article.html"
        article = Article.objects.get()
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["WARNING"],
                message=f'The article \'<a href="/reading/articles/{article.id}-on-the-3-musketeers/">'  # noqa: E501
                f"On the 3 musketeers</a>' was added but we failed to fetch its content. "
                "Please check that it really points to an article.",
            )
        ]

    def test_invalid_form(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, {"url": "Some trash"})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "reading/add_article.html"

    def test_fetch_failure(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("Took too long."))

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "reading/add_article.html"
        article = Article.objects.get()
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["WARNING"],
                message="Failed to fetch the article. Please check that the URL you entered is "
                "correct, that the article exists and is accessible. "
                "We added its URL directly. "
                f'Go <a href="/reading/articles/{article.id}-https-www-example-com-posts-en-1-super-article/'  # noqa: E501
                '">there</a> to access it.',
            )
        ]

    def test_add_already_saved(self, user, logged_in_sync_client, httpx_mock):
        existing_article = ArticleFactory(
            user=user,
            link=self.article_url,
            read_at=utcnow(),
            title="Existing",
            reading_time=10,
            content="Existing content",
            updated_at=utcdt(2024, 3, 1),
        )
        httpx_mock.add_response(text=self.article_content, url=existing_article.link)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "reading/add_article.html"
        article = Article.objects.get()
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["INFO"],
                message=f'Article \'<a href="/reading/articles/{article.id}-{article.slug}/">'
                f"{article.title}</a>' already existed.",
            )
        ]
        assert article.read_at == existing_article.read_at
        assert article.title == existing_article.title
        assert article.slug == existing_article.slug
        assert article.reading_time == existing_article.reading_time
        # Only content must be updated.
        assert article.content != existing_article.content

    def test_fetch_failure_link_already_saved(self, user, logged_in_sync_client, httpx_mock):
        article = ArticleFactory(user=user)
        httpx_mock.add_exception(httpx.ReadTimeout("Took too long."))

        response = logged_in_sync_client.post(
            self.url, {**self.sample_payload, "url": article.link}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "reading/add_article.html"
        messages = list(get_messages(response.wsgi_request))
        assert Article.objects.count() == 1
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="Failed to fetch the article. Please check that the URL you entered is "
                "correct, that the article exists and is accessible. It was added before, "
                "please check its link.",
            )
        ]

    def test_content_too_big(self, logged_in_sync_client, httpx_mock, mocker):
        mocker.patch(
            "legadilo.reading.services.article_fetching.sys.getsizeof",
            return_value=10 * 2048 * 1024,
        )
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "reading/add_article.html"
        article = Article.objects.get()
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["WARNING"],
                message="The article you are trying to fetch is too big and cannot be processed. "
                "We added its URL directly. "
                f'Go <a href="/reading/articles/{article.id}-https-www-example-com-posts-en-1-super-article/"'  # noqa: E501
                ">there</a> to access it.",
            )
        ]


@pytest.mark.django_db
class TestRefetchArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("reading:refetch_article")
        self.article_url = "https://www.example.com/posts/en/1-super-article/"
        self.article = ArticleFactory(
            user=user,
            link=self.article_url,
            slug="initial-slug",
            title="Initial title",
            summary="Initial summary",
            content="Initial content",
        )
        self.existing_tag = TagFactory(title="Existing tag", user=user)
        ArticleTag.objects.create(
            tag=self.existing_tag,
            article=self.article,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )

        self.sample_payload = {"url": self.article_url}

    def test_access_if_not_logged_in(self, client):
        response = client.post(self.url)

        assert_redirected_to_login_page(response)

    def test_access_if_logged_in_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_refetch_article_with_tags(
        self, django_assert_num_queries, logged_in_sync_client, httpx_mock
    ):
        httpx_mock.add_response(
            text=get_article_fixture_content("sample_blog_article.html"), url=self.article_url
        )

        with django_assert_num_queries(14):
            response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"/reading/articles/{self.article.id}-{self.article.slug}/"
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert article.title == self.article.title
        assert article.slug == self.article.slug
        assert article.summary.startswith("I just wrote a new book")
        assert "Lorem ipsum" in article.content
        assert list(article.article_tags.values_list("tag__slug", "tagging_reason")) == [
            ("existing-tag", constants.TaggingReason.FROM_FEED),
        ]

    def test_refetch_article_with_from_url(
        self, django_assert_num_queries, logged_in_sync_client, httpx_mock
    ):
        httpx_mock.add_response(text="", url=self.article_url)

        with django_assert_num_queries(14):
            response = logged_in_sync_client.post(
                self.url,
                self.sample_payload,
                HTTP_REFERER="http://testserver/" + self.url + "?from_url=%2Ftoto%2F",
            )

        assert response.status_code == HTTPStatus.FOUND
        assert (
            response["Location"]
            == f"/reading/articles/{self.article.id}-initial-slug/?from_url=%2Ftoto%2F"
        )
