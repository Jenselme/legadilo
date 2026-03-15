#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.reading.tests.factories import TagFactory


@pytest.mark.django_db
class TestTagAutocompleteView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("reading:tags_autocomplete")
        self.tag = TagFactory(user=user, title="Tag")
        self.tag_with_sub_tag = TagFactory(user=user, title="Tag with sub tag")
        self.sub_tag = TagFactory(user=user, title="Sub tag")
        self.tag_with_sub_tag.sub_tags.add(self.sub_tag)
        self.some_tag = TagFactory(user=user, title="Some title")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url, data={"query": "tag"})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == []

    def test_list(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url, data={"query": "tag"})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == [
            {"hierarchy": [], "label": self.sub_tag.title, "value": self.sub_tag.slug},
            {"hierarchy": [], "label": self.tag.title, "value": self.tag.slug},
            {
                "hierarchy": [{"slug": self.sub_tag.slug, "title": self.sub_tag.title}],
                "label": self.tag_with_sub_tag.title,
                "value": self.tag_with_sub_tag.slug,
            },
        ]

    def test_list_without_hierarchy(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url, data={"query": "tag", "hierarchy": "false"})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == [
            {"label": self.sub_tag.title, "value": self.sub_tag.slug},
            {"label": self.tag.title, "value": self.tag.slug},
            {"label": self.tag_with_sub_tag.title, "value": self.tag_with_sub_tag.slug},
        ]

    def test_list_no_query(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.json() == []
