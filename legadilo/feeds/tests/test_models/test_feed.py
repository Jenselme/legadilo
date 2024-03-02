from datetime import UTC, datetime

import pytest
from asgiref.sync import async_to_sync
from django.db import IntegrityError

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.models import FeedUpdate
from legadilo.feeds.tests.factories import FeedFactory
from legadilo.feeds.utils.feed_parsing import FeedArticle, FeedMetadata
from legadilo.users.tests.factories import UserFactory

from ...models import Feed


@pytest.mark.django_db()
class TestFeedQuerySet:
    def test_only_feeds_to_update(self):
        FeedFactory(enabled=False)
        feed1 = FeedFactory(enabled=True)
        feed2 = FeedFactory(enabled=True)

        feed_ids_to_update = (
            Feed.objects.get_queryset().only_feeds_to_update().values_list("id", flat=True).order_by("id")
        )

        assert list(feed_ids_to_update) == [feed1.id, feed2.id]

        feed_ids_to_update = (
            Feed.objects.get_queryset().only_feeds_to_update([feed1.id]).values_list("id", flat=True).order_by("id")
        )

        assert list(feed_ids_to_update) == [feed1.id]


@pytest.mark.django_db()
class TestFeedManager:
    def test_create_from_url(self, user, mocker):
        mocker.patch(
            "legadilo.feeds.models.feed.get_feed_metadata",
            return_value=FeedMetadata(
                feed_url="https://example.com/feeds/atom.xml",
                site_url="https://example.com",
                title="Awesome website",
                description="A description",
                feed_type=SupportedFeedType.atom,
                etag="W/etag",
                last_modified=None,
                articles=[
                    FeedArticle(
                        article_feed_id="some-article-1",
                        title="Article 1",
                        summary="Summary 1",
                        content="Description 1",
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        link="https//example.com/article/1",
                        published_at=datetime.now(tz=UTC),
                        updated_at=datetime.now(tz=UTC),
                    )
                ],
            ),
            autospec=True,
        )

        feed = async_to_sync(Feed.objects.create_from_url)("https://example.com/feeds/atom.xml", user)

        assert Feed.objects.all().count() == 1
        assert feed.id > 0
        assert feed.feed_url == "https://example.com/feeds/atom.xml"
        assert feed.site_url == "https://example.com"
        assert feed.title == "Awesome website"
        assert feed.description == "A description"
        assert feed.feed_type == SupportedFeedType.atom
        assert feed.articles.count() > 0
        feed_update = async_to_sync(FeedUpdate.objects.get_latest_success_for_feed)(feed)
        assert feed_update.success
        assert not feed_update.error_message
        assert feed_update.feed_etag == "W/etag"
        assert feed_update.feed_last_modified is None

    def test_cannot_create_duplicated_feed_for_same_user(self, user, mocker):
        mocker.patch(
            "legadilo.feeds.models.feed.get_feed_metadata",
            return_value=FeedMetadata(
                feed_url="https://example.com/feeds/atom.xml",
                site_url="https://example.com",
                title="Awesome website",
                description="A description",
                feed_type=SupportedFeedType.atom,
                etag="W/etag",
                last_modified=None,
                articles=[],
            ),
            autospec=True,
        )
        FeedFactory(feed_url="https://example.com/feeds/atom.xml", user=user)

        with pytest.raises(IntegrityError) as execinfo:
            async_to_sync(Feed.objects.create_from_url)("https://example.com/feeds/atom.xml", user)

        assert 'duplicate key value violates unique constraint "feeds_Feed_feed_url_unique"' in str(execinfo.value)

    def test_can_create_duplicated_feed_for_different_user(self, user, mocker):
        mocker.patch(
            "legadilo.feeds.models.feed.get_feed_metadata",
            return_value=FeedMetadata(
                feed_url="https://example.com/feeds/atom.xml",
                site_url="https://example.com",
                title="Awesome website",
                description="A description",
                feed_type=SupportedFeedType.atom,
                etag="W/etag",
                last_modified=None,
                articles=[],
            ),
            autospec=True,
        )
        other_user = UserFactory()
        FeedFactory(feed_url="https://example.com/feeds/atom.xml", user=other_user)

        async_to_sync(Feed.objects.create_from_url)("https://example.com/feeds/atom.xml", user)

        assert list(Feed.objects.values_list("feed_url", flat=True)) == [
            "https://example.com/feeds/atom.xml",
            "https://example.com/feeds/atom.xml",
        ]


@pytest.mark.django_db()
class TestFeed:
    def test_disable(self):
        feed = FeedFactory()

        feed.disable("Broken!")

        assert not feed.enabled
        assert feed.disabled_reason == "Broken!"
        # Check constraint allows save.
        feed.save()
