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

import jwt
import pytest
import time_machine
from django.urls import reverse

from config import settings
from legadilo.users.api import _create_jwt
from legadilo.users.tests.factories import ApplicationTokenFactory
from legadilo.utils.testing import build_bearer_header
from legadilo.utils.time_utils import utcdt


@pytest.mark.django_db
class TestGetRefreshTokenView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("api-1.0.0:refresh_token")
        self.application_token = ApplicationTokenFactory(user=user)

    def test_get_refresh_token_invalid_payload(self, client):
        response = client.post(self.url, {}, content_type="application/json")

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {
                    "loc": ["body", "payload", "application_token"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ]
        }

    def test_get_refresh_token_invalid_token(self, client):
        response = client.post(
            self.url, {"application_token": "inexistent"}, content_type="application/json"
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    @time_machine.travel("2024-11-24 16:30:00", tick=False)
    def test_get_refresh_token(self, client, user, django_assert_num_queries):
        with django_assert_num_queries(2):
            response = client.post(
                self.url,
                {"application_token": self.application_token.token},
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.OK
        assert list(response.json().keys()) == ["jwt"]
        self.application_token.refresh_from_db()
        assert self.application_token.last_used_at == utcdt(2024, 11, 24, 16, 30)
        decoded_jwt = jwt.decode(
            response.json()["jwt"], settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        exp = utcdt(2024, 11, 24, 16, 30) + settings.JWT_MAX_AGE
        assert decoded_jwt == {
            "application_token_title": self.application_token.title,
            "exp": exp.timestamp(),
            "user_id": user.id,
        }


@pytest.mark.django_db
class TestGetUserView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("api-1.0.0:user_info")
        self.application_token = ApplicationTokenFactory(user=user)

    def test_get_user_info_no_token(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user(self, client, user, django_assert_num_queries):
        jwt = _create_jwt(user.id, self.application_token.token)

        with django_assert_num_queries(1):
            response = client.get(
                self.url,
                HTTP_AUTHORIZATION=build_bearer_header(jwt),
            )

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"email": user.email}

    def test_get_user_expired_token(self, client, user):
        with time_machine.travel("2024-11-20 16:30:00"):
            jwt = _create_jwt(user.id, self.application_token.token)

        response = client.get(
            self.url,
            HTTP_AUTHORIZATION=build_bearer_header(jwt),
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user_invalid_token(self, client, user):
        response = client.get(
            self.url,
            HTTP_AUTHORIZATION=build_bearer_header("toto"),
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED
