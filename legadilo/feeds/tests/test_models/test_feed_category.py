import pytest

from legadilo.feeds.models import FeedCategory
from legadilo.feeds.tests.factories import FeedCategoryFactory


@pytest.mark.django_db()
class TestFeedCategoryQuerySet:
    def test_for_user(self, user):
        feed_category = FeedCategoryFactory(user=user)
        FeedCategoryFactory()

        categories_for_user = FeedCategory.objects.get_queryset().for_user(user)

        assert list(categories_for_user) == [feed_category]


@pytest.mark.django_db()
class TestFeedCategoryManager:
    def test_get_all_choices(self, user):
        feed_category = FeedCategoryFactory(user=user)
        FeedCategoryFactory()

        categories_for_user = FeedCategory.objects.get_all_choices(user)

        assert list(categories_for_user) == [("", "None"), (feed_category.slug, feed_category.name)]
