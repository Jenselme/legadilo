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

from http import HTTPStatus

import jwt
import pytest
import time_machine
from django.urls import reverse

from config import settings
from legadilo.users.models import ApplicationToken
from legadilo.utils.time_utils import utcdt


@pytest.mark.django_db
class TestGetRefreshTokenView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("api-1.0.0:create_tokens")
        self.application_token, self.token_secret = ApplicationToken.objects.create_new_token(
            user=user, title="My token", validity_end=None
        )

    def test_get_access_token_invalid_payload(self, client):
        response = client.post(self.url, {}, content_type="application/json")

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {"loc": ["body", "payload", "email"], "msg": "Field required", "type": "missing"},
                {
                    "loc": ["body", "payload", "application_token_uuid"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "loc": ["body", "payload", "application_token_secret"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ]
        }

    def test_get_access_token_invalid_token(self, user, client):
        response = client.post(
            self.url,
            {
                "email": user.email,
                "application_token_uuid": self.application_token.uuid,
                "application_token_secret": "some secret",
            },
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json() == {"detail": "Invalid credentials."}

    @time_machine.travel("2024-11-24 16:30:00", tick=False)
    def test_get_access_token(self, client, user, django_assert_num_queries):
        with django_assert_num_queries(2):
            response = client.post(
                self.url,
                {
                    "email": user.email,
                    "application_token_uuid": self.application_token.uuid,
                    "application_token_secret": self.token_secret,
                },
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.OK
        assert list(response.json().keys()) == ["access_token"]
        self.application_token.refresh_from_db()
        assert self.application_token.last_used_at == utcdt(2024, 11, 24, 16, 30)
        decoded_jwt = jwt.decode(
            response.json()["access_token"],
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        exp = utcdt(2024, 11, 24, 16, 30) + settings.ACCESS_TOKEN_MAX_AGE
        assert decoded_jwt == {
            "application_token_uuid": str(self.application_token.uuid),
            "exp": exp.timestamp(),
        }


@pytest.mark.django_db
class TestGetUserView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("api-1.0.0:user_info")
        self.application_token, self.token_secret = ApplicationToken.objects.create_new_token(
            user=user, title="My token", validity_end=None
        )

    def _get_authorization_header(self, client, user):
        jwt = client.post(
            reverse("api-1.0.0:create_tokens"),
            {
                "email": user.email,
                "application_token_uuid": self.application_token.uuid,
                "application_token_secret": self.token_secret,
            },
            content_type="application/json",
        ).json()["access_token"]

        return f"Bearer {jwt}"

    def test_get_user_info_no_token(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user(self, client, user, django_assert_num_queries):
        header = self._get_authorization_header(client, user)

        with django_assert_num_queries(1):
            response = client.get(
                self.url,
                HTTP_AUTHORIZATION=header,
            )

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"email": user.email}

    def test_get_inactive_user(self, client, user, django_assert_num_queries):
        header = self._get_authorization_header(client, user)
        user.is_active = False
        user.save()

        with django_assert_num_queries(1):
            response = client.get(
                self.url,
                HTTP_AUTHORIZATION=header,
            )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user_expired_jwt(self, client, user):
        with time_machine.travel("2024-11-20 16:30:00"):
            header = self._get_authorization_header(client, user)

        response = client.get(
            self.url,
            HTTP_AUTHORIZATION=header,
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user_expired_application_token(self, client, user):
        header = self._get_authorization_header(client, user)
        self.application_token.validity_end = utcdt(2024, 11, 24)
        self.application_token.save()

        response = client.get(
            self.url,
            HTTP_AUTHORIZATION=header,
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user_invalid_token(self, client, user):
        response = client.get(
            self.url,
            HTTP_AUTHORIZATION="Bearer toto",
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED
