#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
import pytest

from legadilo.reading.models import ArticlesGroup
from legadilo.reading.tests.factories import TagFactory


@pytest.mark.django_db
class TestArticlesGroupManager:
    def test_create_with_tags(self, user, django_assert_num_queries):
        tag = TagFactory(title="existing-tag")

        with django_assert_num_queries(5):
            group = ArticlesGroup.objects.create_with_tags(
                user, title="New group", description="Description", tags=[tag]
            )

        assert set(group.tags.values_list("title", flat=True)) == {"existing-tag"}
        assert group.user == user
        assert group.title == "New group"
        assert group.slug == "new-group"
        assert group.description == "Description"
