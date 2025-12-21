#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.reading.tests.factories import ArticlesGroupFactory


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
        assert response.context_data["groups"].count() == 0

    def test_list(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context_data["groups"].count() == 1

    def test_search(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url, data={"q": "Something"})

        assert response.status_code == HTTPStatus.OK
        assert response.context_data["groups"].count() == 0
