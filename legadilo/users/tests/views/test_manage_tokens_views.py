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

from datetime import datetime
from http import HTTPStatus

import pytest
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.core.models import Timezone
from legadilo.users.models import ApplicationToken
from legadilo.users.tests.factories import ApplicationTokenFactory
from legadilo.utils.time_utils import utcdt


@pytest.mark.django_db
class TestManageTokensView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("users:manage_tokens")
        self.application_token = ApplicationTokenFactory(user=user)

    def test_list_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_list(self, logged_in_sync_client, other_user, django_assert_num_queries):
        ApplicationTokenFactory(user=other_user)

        with django_assert_num_queries(8):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "users/manage_tokens.html"
        assert response.context_data["new_application_token"] is None
        assert response.context_data["new_application_token_secret"] is None
        assert list(response.context_data["tokens"]) == [self.application_token]

    def test_create_token_invalid_form(
        self, user, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.post(self.url, data={})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "users/manage_tokens.html"
        assert response.context_data["new_application_token"] is None
        assert response.context_data["new_application_token_secret"] is None
        assert response.context_data["form"].errors == {"title": ["This field is required."]}

    def test_create_token(self, user, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(11):
            response = logged_in_sync_client.post(self.url, data={"title": "Test token"})

        assert response.status_code == HTTPStatus.OK
        assert ApplicationToken.objects.count() == 2
        new_token = ApplicationToken.objects.exclude(id=self.application_token.id).get()
        assert new_token.title == "Test token"
        assert new_token.user == user
        assert new_token.validity_end is None
        assert response.template_name == "users/manage_tokens.html"
        assert isinstance(response.context_data["new_application_token"], ApplicationToken)
        assert isinstance(response.context_data["new_application_token_secret"], str)
        assert len(response.context_data["new_application_token_secret"]) == 67
        assert list(response.context_data["tokens"]) == [new_token, self.application_token]

    def test_create_duplicated_token(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(12):
            response = logged_in_sync_client.post(
                self.url, data={"title": self.application_token.title}
            )

        assert response.status_code == HTTPStatus.CONFLICT
        assert ApplicationToken.objects.count() == 1
        assert response.template_name == "users/manage_tokens.html"
        assert response.context_data["new_application_token"] is None
        assert response.context_data["new_application_token_secret"] is None
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="A token already exists with this name.",
            )
        ]

    def test_create_token_with_validity_end(
        self, user, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(11):
            response = logged_in_sync_client.post(
                self.url, data={"title": "Test token", "validity_end": "2024-11-24 12:00:00Z"}
            )

        assert response.status_code == HTTPStatus.OK
        assert ApplicationToken.objects.count() == 2
        new_token = ApplicationToken.objects.exclude(id=self.application_token.id).get()
        assert new_token.title == "Test token"
        assert new_token.user == user
        assert new_token.validity_end == utcdt(2024, 11, 24, 12)

    def test_create_token_with_validity_end_in_timezone(
        self, user, logged_in_sync_client, django_assert_num_queries
    ):
        new_york_tz, _created = Timezone.objects.get_or_create(name="America/New_York")

        with django_assert_num_queries(12):
            response = logged_in_sync_client.post(
                self.url,
                data={
                    "title": "Test token",
                    "validity_end": "2024-11-24 12:00:00Z",
                    "timezone": new_york_tz.id,
                },
            )

        assert response.status_code == HTTPStatus.OK
        assert ApplicationToken.objects.count() == 2
        new_token = ApplicationToken.objects.exclude(id=self.application_token.id).get()
        assert new_token.title == "Test token"
        assert new_token.user == user
        assert new_token.validity_end == datetime(2024, 11, 24, 12, tzinfo=new_york_tz.zone_info)


@pytest.mark.django_db
class TestDeleteTokenView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.application_token = ApplicationTokenFactory(user=user)
        self.url = reverse("users:delete_token", kwargs={"token_id": self.application_token.id})

    def test_delete_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_delete_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert ApplicationToken.objects.count() == 1

    def test_delete(self, logged_in_sync_client, other_user, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.OK
        assert ApplicationToken.objects.count() == 0
