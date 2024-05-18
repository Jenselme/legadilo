import pytest
from django.db import IntegrityError

from legadilo.reading.models.reading_list import ReadingList
from legadilo.reading.tests.factories import ReadingListFactory


@pytest.mark.django_db()
class TestReadingListManager:
    def test_create_default_lists(self, user, other_user):
        ReadingList.objects.create_default_lists(user)
        ReadingList.objects.create_default_lists(other_user)

        assert ReadingList.objects.count() == 12
        assert user.reading_lists.count() == 6
        assert other_user.reading_lists.count() == 6

    def test_get_default_reading_list(self, user):
        ReadingList.objects.create_default_lists(user)

        default_reading_list = ReadingList.objects.get_reading_list(user, reading_list_slug=None)

        assert default_reading_list.is_default
        assert default_reading_list.title == "Unread"

    def test_get_reading_list(self, user):
        slug_to_get = "my-reading-list"
        reading_list_to_get = ReadingListFactory(slug=slug_to_get, user=user)
        ReadingListFactory(slug="other-reading-list", user=user)
        ReadingListFactory(slug=slug_to_get)

        reading_list = ReadingList.objects.get_reading_list(user, slug_to_get)

        assert reading_list == reading_list_to_get


@pytest.mark.django_db()
class TestReadingListModel:
    def test_cannot_create_multiple_default_lists_for_one_user(self, user):
        ReadingListFactory(user=user, is_default=True)

        with pytest.raises(
            IntegrityError,
            match='duplicate key value violates unique constraint "reading_readinglist_enforce_one_default_reading_list"',  # noqa: E501
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
            match='duplicate key value violates unique constraint "reading_readinglist_enforce_slug_unicity"',  # noqa: E501
        ):
            ReadingListFactory(user=user, slug="reading-list")

    def test_can_create_multiple_lists_with_same_slug_different_user(self):
        ReadingListFactory(slug="reading-list")
        ReadingListFactory(slug="reading-list")

        assert ReadingList.objects.count() == 2
