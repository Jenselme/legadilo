from http import HTTPStatus

import httpx
import pytest
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
from django.urls import reverse

from legadilo.feeds.models import Article
from legadilo.feeds.tests.fixtures import get_fixture_file_content


@pytest.mark.django_db()
class TestAddArticle:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("feeds:add_article")
        self.article_url = "https://www.example.com/posts/en/1-super-article/"
        self.article_content = get_fixture_file_content("sample_blog_article.html")
        self.sample_payload = {"url": self.article_url}

    def test_access_if_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_form(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK

    def test_add_article(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Article 'On the 3 musketeers' successfully added!",
            )
        ]
        assert Article.objects.count() == 1

    def test_add_article_no_content(self, logged_in_sync_client, httpx_mock, mocker):
        httpx_mock.add_response(text=self.article_content, url=self.article_url)
        mocker.patch("legadilo.feeds.utils.article_fetching._get_content", return_value="")

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["WARNING"],
                message="The article 'On the 3 musketeers' was added but we failed to fetch its "
                "content. Please check that it really points to an article.",
            )
        ]
        assert Article.objects.count() == 1

    def test_invalid_form(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, {"url": "Some trash"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_fetch_failure(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("Took too long."))

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="Failed to fetch the article. Please check that the URL you entered is "
                "correct, that the article exists and is accessible.",
            )
        ]

    def test_content_too_big(self, logged_in_sync_client, httpx_mock, mocker):
        mocker.patch(
            "legadilo.feeds.utils.article_fetching.sys.getsizeof", return_value=2048 * 1024
        )
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="The article you are trying to fetch is too big and cannot be processed.",
            )
        ]
