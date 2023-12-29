import pytest

from legadilo.users.models import User
from legadilo.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture()
def user(db) -> User:
    return UserFactory()


@pytest.fixture()
def logged_in_async_client(user, async_client):
    async_client.force_login(user)

    return async_client
