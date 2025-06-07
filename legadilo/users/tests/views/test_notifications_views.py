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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.utils.time_utils import utcnow

from ..factories import NotificationFactory


@pytest.mark.django_db
class TestListNotificationsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("users:list_notifications")
        self.notification = NotificationFactory(user=user)

    def test_list_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_list(self, user, other_user, logged_in_sync_client, django_assert_num_queries):
        NotificationFactory(user=other_user)

        with django_assert_num_queries(7):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "users/notifications.html"
        assert list(response.context_data["notifications"]) == [self.notification]

    def test_mark_all_as_read(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "users/notifications.html"
        self.notification.refresh_from_db()
        assert self.notification.is_read

    def test_mark_as_read(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.post(
                self.url, {"notification_id": self.notification.id}
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "users/notifications.html"
        self.notification.refresh_from_db()
        assert self.notification.is_read

    def test_mark_as_unread(self, logged_in_sync_client, django_assert_num_queries):
        self.notification.read_at = utcnow()
        self.notification.save()

        with django_assert_num_queries(8):
            response = logged_in_sync_client.post(
                self.url, {"notification_id": self.notification.id, "mark-as-unread": ""}
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "users/notifications.html"
        self.notification.refresh_from_db()
        assert not self.notification.is_read
