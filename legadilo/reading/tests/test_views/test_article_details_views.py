from http import HTTPStatus
from urllib.parse import urljoin

import pytest
from django.urls import reverse

from legadilo.reading import constants
from legadilo.reading.models import ArticleTag
from legadilo.reading.tests.factories import ArticleFactory, ReadingListFactory, TagFactory


@pytest.mark.django_db()
class TestArticleDetailsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(user=user)
        self.url = reverse(
            "reading:article_details",
            kwargs={"article_id": self.article.id, "article_slug": self.article.slug},
        )

    def test_view_details_if_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_view_details_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_cannot_get_if_slug_is_invalid(self, logged_in_sync_client):
        url = reverse(
            "reading:article_details",
            kwargs={"article_id": self.article.id, "article_slug": "toto"},
        )

        response = logged_in_sync_client.get(url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_view_details(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/article_details.html"
        assert response.context["article"] == self.article
        assert response.context["from_url"] == reverse("reading:default_reading_list")
        assert "edit_tags_form" in response.context

    def test_view_details_with_from_url(self, logged_in_sync_client, django_assert_num_queries):
        from_url = "/reading/lists/unread/"
        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.url, data={"from_url": from_url})

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/article_details.html"
        assert response.context["article"] == self.article
        assert response.context["from_url"] == from_url
        assert "edit_tags_form" in response.context


@pytest.mark.django_db()
class TestUpdateArticleTagsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(user=user)
        self.reading_list = ReadingListFactory(user=user)
        self.tag_to_keep = TagFactory(user=user)
        ArticleTag.objects.create(
            tag=self.tag_to_keep,
            article=self.article,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        self.tag_to_delete = TagFactory(user=user)
        ArticleTag.objects.create(
            tag=self.tag_to_delete,
            article=self.article,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        self.deleted_tag_to_readd = TagFactory(user=user)
        ArticleTag.objects.create(
            tag=self.deleted_tag_to_readd,
            article=self.article,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        self.existing_tag_to_add = TagFactory(user=user)
        self.some_other_tag = TagFactory(user=user)
        self.reading_list_url = reverse(
            "reading:reading_list", kwargs={"reading_list_slug": self.reading_list.slug}
        )
        self.url = reverse(
            "reading:update_article_tags",
            kwargs={
                "article_id": self.article.id,
            },
        )
        self.sample_payload = {
            "tags": [
                self.tag_to_keep.slug,
                self.existing_tag_to_add.slug,
                self.deleted_tag_to_readd.slug,
                "Some tag",
            ]
        }

    def test_cannot_access_if_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_access_article_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_tags_for_article_details(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        referer_url = urljoin("http://testserver/", self.reading_list_url)
        with django_assert_num_queries(14):
            response = logged_in_sync_client.post(
                self.url,
                {**self.sample_payload, "for_article_details": True},
                HTTP_REFERER=referer_url,
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == referer_url
        assert list(self.article.article_tags.values_list("tag__slug", "tagging_reason")) == [
            ("some-tag", constants.TaggingReason.ADDED_MANUALLY),
            (self.tag_to_keep.slug, constants.TaggingReason.ADDED_MANUALLY),
            (self.tag_to_delete.slug, constants.TaggingReason.DELETED),
            (self.deleted_tag_to_readd.slug, constants.TaggingReason.ADDED_MANUALLY),
            (self.existing_tag_to_add.slug, constants.TaggingReason.ADDED_MANUALLY),
        ]
