# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.core.utils.time_utils import utcnow

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
