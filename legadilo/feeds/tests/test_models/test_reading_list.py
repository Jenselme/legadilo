import pytest
from django.db import IntegrityError

from legadilo.feeds.models.reading_list import ReadingList
from legadilo.feeds.tests.factories import ReadingListFactory


@pytest.mark.django_db()
class TestReadingListManager:
    def test_create_default_lists(self, user):
        ReadingList.objects.create_default_lists(user)

        assert ReadingList.objects.count() == 5
        assert user.reading_lists.count() == 5


@pytest.mark.django_db()
class TestReadingListModel:
    def test_cannot_create_multiple_default_lists_for_one_user(self, user):
        ReadingListFactory(user=user, is_default=True)

        with pytest.raises(
            IntegrityError,
            match='duplicate key value violates unique constraint "feeds_readinglist_enforce_one_default_reading_list"',  # noqa: E501
        ):
            ReadingListFactory(user=user, is_default=True)

    def test_can_create_multiple_default_lists_for_another_user(self):
        ReadingListFactory(is_default=True)
        ReadingListFactory(is_default=True)

        assert ReadingList.objects.count() == 2

    def test_cannot_create_multiple_lists_with_same_slug_for_one_user(self, user):
        ReadingListFactory(user=user, slug="reading-list")

        with pytest.raises(
            IntegrityError,
            match='duplicate key value violates unique constraint "feeds_readinglist_enforce_slug_unicity"',  # noqa: E501
        ):
            ReadingListFactory(user=user, slug="reading-list")

    def test_can_create_multiple_lists_with_same_slug_different_user(self):
        ReadingListFactory(slug="reading-list")
        ReadingListFactory(slug="reading-list")

        assert ReadingList.objects.count() == 2
