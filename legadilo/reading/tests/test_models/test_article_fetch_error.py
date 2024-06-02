import pytest
import time_machine

from legadilo.reading.models import ArticleFetchError
from legadilo.reading.tests.factories import ArticleFetchErrorFactory


@pytest.mark.django_db()
class TestArticleFetchErrorQuerySet:
    def test_for_cleanup(self):
        with time_machine.travel("2024-03-15 12:00:00"):
            object_to_cleanup = ArticleFetchErrorFactory()
        with time_machine.travel("2024-05-01 12:00:00"):
            ArticleFetchErrorFactory()

        with time_machine.travel("2024-06-01 12:00:00"):
            article_fetch_errors = ArticleFetchError.objects.get_queryset().for_cleanup()

        assert list(article_fetch_errors) == [object_to_cleanup]
