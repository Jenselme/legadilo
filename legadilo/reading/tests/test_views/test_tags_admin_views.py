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
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.reading.models import Tag
from legadilo.reading.models.tag import SubTagMapping
from legadilo.reading.tests.factories import TagFactory


@pytest.mark.django_db
class TestTagsAdminView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("reading:tags_admin")
        self.tag = TagFactory(user=user)

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_list(self, logged_in_sync_client, django_assert_num_queries):
        TagFactory(title="Tag other user")

        with django_assert_num_queries(7):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/tags_admin.html"
        assert response.context_data["tags"] == [self.tag]


@pytest.mark.django_db
class TestCreateTagView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("reading:create_tag")
        self.tag = TagFactory(user=user)
        self.tag_other_user = TagFactory()

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_view_page(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(9):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/edit_tag.html"

    def test_create_tag(self, logged_in_sync_client, django_assert_num_queries, user):
        with django_assert_num_queries(17):
            response = logged_in_sync_client.post(self.url, {"title": "Tag to create"})

        assert response.status_code == HTTPStatus.FOUND
        created_tag = Tag.objects.get(title="Tag to create")
        assert created_tag.user == user
        assert response["Location"] == reverse("reading:edit_tag", kwargs={"pk": created_tag.id})

    def test_create_tag_already_exists(
        self, logged_in_sync_client, django_assert_num_queries, user
    ):
        with django_assert_num_queries(15):
            response = logged_in_sync_client.post(self.url, {"title": self.tag.title})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:edit_tag", kwargs={"pk": self.tag.id})


@pytest.mark.django_db
class TestEditTagView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag = TagFactory(title="The title", user=user)
        self.url = reverse("reading:edit_tag", kwargs={"pk": self.tag.id})

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_view_page(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(12):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/edit_tag.html"
        assert response.context_data["tag"] == self.tag

    def test_delete_tag(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(self.url, {"delete": "true"})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:tags_admin")
        assert Tag.objects.count() == 0

    def test_delete_tag_with_sub_tags(self, user, logged_in_sync_client, django_assert_num_queries):
        sub_tag = TagFactory(title="Sub tag", user=user)
        SubTagMapping.objects.create(base_tag=self.tag, sub_tag=sub_tag)

        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(self.url, {"delete": "true"})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:tags_admin")
        assert Tag.objects.count() == 1
        assert Tag.objects.get() == sub_tag

    def test_delete_sub_tag(self, user, logged_in_sync_client, django_assert_num_queries):
        top_tag = TagFactory(title="Top tag", user=user)
        SubTagMapping.objects.create(base_tag=top_tag, sub_tag=self.tag)
        url = reverse("reading:edit_tag", kwargs={"pk": top_tag.id})

        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(url, {"delete": "true"})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:tags_admin")
        assert Tag.objects.count() == 1
        assert Tag.objects.get() == self.tag

    def test_delete_tag_with_htmx(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                self.url, {"delete": "true"}, HTTP_HX_Request="true"
            )

        assert response.status_code == HTTPStatus.OK
        assert response["HX-Redirect"] == reverse("reading:tags_admin")
        assert response["HX-Push-Url"] == "true"
        assert Tag.objects.count() == 0

    def test_update_tag(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(14):
            response = logged_in_sync_client.post(self.url, {"title": "Updated title"})

        assert response.status_code == HTTPStatus.OK
        self.tag.refresh_from_db()
        assert self.tag.title == "Updated title"
        assert self.tag.slug == "updated-title"
        assert self.tag.sub_tags.count() == 0

    def test_clear_sub_tags(self, user, logged_in_sync_client, django_assert_num_queries):
        sub_tag = TagFactory(title="Sub tag", user=user)
        SubTagMapping.objects.create(base_tag=self.tag, sub_tag=sub_tag)

        with django_assert_num_queries(20):
            response = logged_in_sync_client.post(self.url, {"title": "Updated title"})

        assert response.status_code == HTTPStatus.OK
        self.tag.refresh_from_db()
        assert self.tag.sub_tags.count() == 0

    def test_update_sub_tags(self, user, logged_in_sync_client, django_assert_num_queries):
        sub_tag = TagFactory(title="Sub tag", user=user)
        SubTagMapping.objects.create(base_tag=self.tag, sub_tag=sub_tag)
        existing_sub_tag = TagFactory(title="Existing tag", user=user)

        with django_assert_num_queries(23):
            response = logged_in_sync_client.post(
                self.url,
                {"title": "Updated title", "sub_tags": [existing_sub_tag.slug, "Tag to create"]},
            )

        assert response.status_code == HTTPStatus.OK
        self.tag.refresh_from_db()
        assert set(self.tag.sub_tags.values_list("slug", flat=True)) == {
            existing_sub_tag.slug,
            "tag-to-create",
        }