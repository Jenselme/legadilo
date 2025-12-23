#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.core.utils.time_utils import utcdt
from legadilo.reading.models import Article, ArticlesGroup
from legadilo.reading.tests.factories import ArticleFactory, ArticlesGroupFactory, TagFactory


@pytest.mark.django_db
class TestArticlesGroupDetailsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.group = ArticlesGroupFactory(user=user, title="My group")
        self.article = ArticleFactory(user=user, group=self.group, group_order=1, read_at=None)
        self.url = reverse(
            "reading:articles_group_details",
            kwargs={"group_id": self.group.id, "group_slug": self.group.slug},
        )
        other_group = ArticlesGroupFactory(user=user)
        ArticleFactory(user=user, group=other_group, read_at=None)

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("account_login") + f"?next={self.url}"

    def test_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_details(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(12):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/articles_group_details.html"
        assert response.context_data["group"] == self.group

    def test_mark_all_articles_as_read(
        self, user, logged_in_sync_client, django_assert_num_queries
    ):
        read_at = utcdt(2025, 1, 1)
        initially_read_article = ArticleFactory(
            user=user, group=self.group, group_order=2, read_at=read_at
        )
        ArticleFactory(user=user, read_at=None)

        with django_assert_num_queries(16):
            response = logged_in_sync_client.post(self.url, {"mark_all_as_read": ""})

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/articles_group_details.html"
        assert Article.objects.filter(read_at__isnull=False).count() == 2
        initially_read_article.refresh_from_db()
        assert initially_read_article.read_at == read_at
        assert self.group.articles.all().filter(read_at__isnull=True).count() == 0

    def test_delete_group(self, user, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(12):
            response = logged_in_sync_client.post(self.url, {"action": "delete_group"})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:articles_groups_list")
        assert ArticlesGroup.objects.filter(id=self.group.id).count() == 0
        assert Article.objects.count() == 2
        self.article.refresh_from_db()
        assert self.article.group_id is None

    def test_delete_group_and_all_its_articles(
        self, user, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(18):
            response = logged_in_sync_client.post(
                self.url, {"action": "delete_group_and_all_articles"}
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:articles_groups_list")
        assert ArticlesGroup.objects.filter(id=self.group.id).count() == 0
        assert Article.objects.count() == 1
        assert Article.objects.get().id != self.article.id

    def test_update_group(self, user, logged_in_sync_client, django_assert_num_queries):
        tag_to_unlink = TagFactory(user=user, title="Tag to unlink")
        self.group.tags.add(tag_to_unlink)
        existing_tag = TagFactory(user=user, title="Tag to link")

        with django_assert_num_queries(30):
            response = logged_in_sync_client.post(
                self.url,
                {
                    "title": "Updated title",
                    "description": "New description",
                    "tags": [existing_tag.slug, "New tag"],
                    "action": "update_articles_group",
                },
            )

        assert response.status_code == HTTPStatus.OK
        self.group.refresh_from_db()
        assert self.group.title == "Updated title"
        assert self.group.description == "New description"
        assert set(self.group.articles_group_tags.get_selected_values()) == {
            existing_tag.slug,
            "new-tag",
        }

    def test_update_group_invalid_form(self, user, logged_in_sync_client):
        response = logged_in_sync_client.post(
            self.url,
            {"title": "", "description": "", "tags": [], "action": "update_articles_group"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.context_data["edit_articles_group_form"].errors == {
            "title": ["This field is required."],
        }


@pytest.mark.django_db
class TestArticlesGroupReadAllArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.group = ArticlesGroupFactory(user=user, title="My group")
        self.article = ArticleFactory(user=user, group=self.group, group_order=1, read_at=None)
        self.url = reverse(
            "reading:article_groups_read_all_articles",
            kwargs={"group_id": self.group.id, "group_slug": self.group.slug},
        )
        other_group = ArticlesGroupFactory(user=user)
        ArticleFactory(user=user, group=other_group, read_at=None)

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("account_login") + f"?next={self.url}"

    def test_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(10):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/articles_group_read_all_articles.html"
        assert response.context_data["group"] == self.group

    def test_mark_all_as_read(self, user, logged_in_sync_client, django_assert_num_queries):
        read_at = utcdt(2025, 1, 1)
        initially_read_article = ArticleFactory(
            user=user, group=self.group, group_order=2, read_at=read_at
        )
        ArticleFactory(user=user, read_at=None)

        with django_assert_num_queries(8):
            response = logged_in_sync_client.post(self.url, {})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse(
            "reading:articles_group_details",
            kwargs={"group_id": self.group.id, "group_slug": self.group.slug},
        )
        assert Article.objects.filter(read_at__isnull=False).count() == 2
        assert self.group.articles.all().filter(read_at__isnull=True).count() == 0
        initially_read_article.refresh_from_db()
        assert initially_read_article.read_at == read_at


@pytest.mark.django_db
class TestArticlesGroupsListView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user, other_user):
        self.url = reverse("reading:articles_groups_list")
        self.group = ArticlesGroupFactory(user=user, title="My group")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("account_login") + f"?next={self.url}"

    def test_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert list(response.context_data["groups_page"].object_list) == []

    def test_list(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context_data["groups_page"].object_list == [self.group]

    def test_search(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url, data={"q": "Something"})

        assert response.status_code == HTTPStatus.OK
        assert list(response.context_data["groups_page"].object_list) == []

    def test_search_with_tags(self, user, logged_in_sync_client):
        tag = TagFactory(user=user, title="test")
        self.group.tags.add(tag)

        response = logged_in_sync_client.get(self.url, data={"tags": [tag.slug]})

        assert response.status_code == HTTPStatus.OK
        assert list(response.context_data["groups_page"].object_list) == [self.group]

    def test_invalid_search_form(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url, data={"q": "a"})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.context_data["form"].errors == {
            "q": ["Ensure this value has at least 3 characters (it has 1)."]
        }
