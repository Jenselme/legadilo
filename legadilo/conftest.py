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

import pytest

from legadilo.users.models import User
from legadilo.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _setup_settings(settings, tmpdir):
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


@pytest.fixture()
def user(db) -> User:
    return UserFactory()


@pytest.fixture()
def other_user(db) -> User:
    return UserFactory()


@pytest.fixture()
def logged_in_sync_client(user, client):
    client.force_login(user)
    return client


@pytest.fixture()
def logged_in_other_user_sync_client(other_user, client):
    client.force_login(other_user)
    return client
