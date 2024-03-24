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
def logged_in_sync_client(user, client):
    client.force_login(user)
    return client
