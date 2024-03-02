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
def logged_in_sync_client(user, client):
    client.force_login(user)
    return client
