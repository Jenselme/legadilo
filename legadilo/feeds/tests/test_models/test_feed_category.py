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

    def test_get_first_for_user(self, user, other_user):
        feed_category_user = FeedCategoryFactory(user=user, name="Slug", slug="slug")
        FeedCategoryFactory(user=other_user, name="Slug", slug="slug")

        found_category = FeedCategory.objects.get_first_for_user(user, "slug")
        inexistant_slug = FeedCategory.objects.get_first_for_user(user, "some trash")

        assert found_category == feed_category_user
        assert inexistant_slug is None
