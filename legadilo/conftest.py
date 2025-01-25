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

import pytest
from allauth.conftest import reauthentication_bypass as allauth_reauthentication_bypass
from django.urls import reverse

from legadilo.core.models import Timezone
from legadilo.users.models import User
from legadilo.users.tests.factories import UserFactory, UserSettingsFactory

reauthentication_bypass = allauth_reauthentication_bypass


@pytest.fixture(autouse=True)
def _setup_settings(settings, tmpdir):
    settings.IS_PRODUCTION = True
    # https://docs.djangoproject.com/en/dev/ref/settings/#media-url
    settings.MEDIA_URL = "http://media.testserver"
    settings.MEDIA_ROOT = tmpdir.strpath
    settings.STORAGES["staticfiles"]["BACKEND"] = (
        "django.contrib.staticfiles.storage.StaticFilesStorage"
    )
    # https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    # https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.TEMPLATES[0]["OPTIONS"]["debug"] = True


@pytest.fixture
def user(db) -> User:
    return UserFactory()


@pytest.fixture
def other_user(db) -> User:
    return UserFactory()


@pytest.fixture
def utc_tz(db) -> Timezone:
    # The Timezone table will be filled when the db is created from migrations and deleted at the
    # end of the test suite. So we have to use get_or_create here.
    return Timezone.objects.get_or_create(name="UTC")[0]


@pytest.fixture
def admin_user(admin_user, utc_tz) -> User:
    admin_user.settings = UserSettingsFactory(user=admin_user, timezone=utc_tz)
    admin_user.save()
    return admin_user


@pytest.fixture
def logged_in_sync_client(user, client):
    client.force_login(user)
    return client


@pytest.fixture
def logged_in_other_user_sync_client(other_user, client):
    client.force_login(other_user)
    return client


def assert_redirected_to_login_page(response):
    assert response.status_code == HTTPStatus.FOUND  # noqa: S101 use of assert detected
    assert reverse("account_login") in response["Location"]  # noqa: S101 use of assert detected
