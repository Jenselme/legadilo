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

import pytest
from django.db import IntegrityError

from legadilo.reading.models.reading_list import ReadingList
from legadilo.reading.tests.factories import ReadingListFactory


@pytest.mark.django_db
class TestReadingListManager:
    def test_create_default_lists(self, user, other_user):
        ReadingList.objects.create_default_lists(user)
        ReadingList.objects.create_default_lists(other_user)

        assert ReadingList.objects.count() == 10
        assert user.reading_lists.count() == 5
        assert other_user.reading_lists.count() == 5

    def test_get_default_reading_list(self, user):
        ReadingList.objects.create_default_lists(user)

        default_reading_list = ReadingList.objects.get_reading_list(user, reading_list_slug=None)

        assert default_reading_list.is_default
        assert default_reading_list.title == "Unread"

    def test_get_reading_list(self, user):
        slug_to_get = "my-reading-list"
        reading_list_to_get = ReadingListFactory(title="My Reading list", user=user)
        ReadingListFactory(title="My Other Reading list", user=user)
        ReadingListFactory(title="My Reading list")

        reading_list = ReadingList.objects.get_reading_list(user, slug_to_get)

        assert reading_list == reading_list_to_get

    def test_make_default(self, user):
        initial_default_reading_list = ReadingListFactory(user=user, is_default=True)
        reading_list = ReadingListFactory(user=user, is_default=False)

        ReadingList.objects.make_default(reading_list)

        reading_list.refresh_from_db()
        initial_default_reading_list.refresh_from_db()
        assert reading_list.is_default
        assert not initial_default_reading_list.is_default


@pytest.mark.django_db
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
        ReadingListFactory(user=user, title="Reading list")

        with pytest.raises(
            IntegrityError,
            match='duplicate key value violates unique constraint "reading_readinglist_enforce_slug_unicity"',  # noqa: E501
        ):
            ReadingListFactory(user=user, title="Reading list")

    def test_can_create_multiple_lists_with_same_slug_different_user(self):
        ReadingListFactory(title="Reading List")
        ReadingListFactory(title="Reading List")

        assert ReadingList.objects.count() == 2
