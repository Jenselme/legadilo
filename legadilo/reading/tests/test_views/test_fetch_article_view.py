from http import HTTPStatus

import httpx
import pytest
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
from django.urls import reverse

from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag
from legadilo.reading.tests.factories import ArticleFactory, TagFactory
from legadilo.reading.tests.fixtures import get_article_fixture_content


@pytest.mark.django_db()
class TestAddArticle:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("reading:add_article")
        self.article_url = "https://www.example.com/posts/en/1-super-article/"
        self.article_content = get_article_fixture_content("sample_blog_article.html")
        self.existing_tag = TagFactory(name="Existing tag", user=user)
        self.sample_payload = {"url": self.article_url}
        self.payload_with_tags = {
            "url": self.article_url,
            "tags": [self.existing_tag.slug, "New", "Tag with spaces"],
        }

    def test_access_if_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_form(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/add_article.html"

    def test_add_article(self, django_assert_num_queries, logged_in_sync_client, httpx_mock):
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        with django_assert_num_queries(11):
            response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "feeds/add_article.html"
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Article 'On the 3 musketeers' successfully added!",
            )
        ]
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert list(article.tags.all()) == []

    def test_add_article_with_tags(
        self, django_assert_num_queries, logged_in_sync_client, httpx_mock
    ):
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        with django_assert_num_queries(15):
            response = logged_in_sync_client.post(self.url, self.payload_with_tags)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "feeds/add_article.html"
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Article 'On the 3 musketeers' successfully added!",
            )
        ]
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert list(article.article_tags.values_list("tag__slug", "tagging_reason")) == [
            ("existing-tag", constants.TaggingReason.ADDED_MANUALLY),
            ("new", constants.TaggingReason.ADDED_MANUALLY),
            ("tag-with-spaces", constants.TaggingReason.ADDED_MANUALLY),
        ]

    def test_add_article_no_content(self, logged_in_sync_client, httpx_mock, mocker):
        httpx_mock.add_response(text=self.article_content, url=self.article_url)
        mocker.patch("legadilo.reading.utils.article_fetching._get_content", return_value="")

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "feeds/add_article.html"
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
        assert response.template_name == "feeds/add_article.html"

    def test_fetch_failure(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("Took too long."))

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
        assert response.template_name == "feeds/add_article.html"
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
            "legadilo.reading.utils.article_fetching.sys.getsizeof", return_value=2048 * 1024
        )
        httpx_mock.add_response(text=self.article_content, url=self.article_url)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "feeds/add_article.html"
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="The article you are trying to fetch is too big and cannot be processed.",
            )
        ]


@pytest.mark.django_db()
class TestRefetchArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("reading:refetch_article")
        self.article_url = "https://www.example.com/posts/en/1-super-article/"
        self.article = ArticleFactory(user=user, link=self.article_url)
        self.existing_tag = TagFactory(name="Existing tag", user=user)
        ArticleTag.objects.create(
            tag=self.existing_tag,
            article=self.article,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )

        self.sample_payload = {"url": self.article_url}

    def test_access_if_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_refetch_article_with_tags(
        self, django_assert_num_queries, logged_in_sync_client, httpx_mock
    ):
        httpx_mock.add_response(text="", url=self.article_url)

        with django_assert_num_queries(9):
            response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:default_reading_list")
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert list(article.article_tags.values_list("tag__slug", "tagging_reason")) == [
            ("existing-tag", constants.TaggingReason.FROM_FEED),
        ]
