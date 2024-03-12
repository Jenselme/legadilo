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
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.default_feed_url = "https://example.com/feeds/atom.exsiting.xml"
        self.feed = FeedFactory(feed_url=self.default_feed_url, user=user)
        self.initial_feed_count = 1

    def test_create_from_metadata(self, user):
        feed = Feed.objects.create_from_metadata(
            FeedMetadata(
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
            user,
        )

        assert Feed.objects.all().count() == self.initial_feed_count + 1
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

    def test_cannot_create_duplicated_feed_for_same_user(self, user):
        with pytest.raises(IntegrityError) as execinfo:
            Feed.objects.create_from_metadata(
                FeedMetadata(
                    feed_url=self.default_feed_url,
                    site_url="https://example.com",
                    title="Awesome website",
                    description="A description",
                    feed_type=SupportedFeedType.atom,
                    etag="W/etag",
                    last_modified=None,
                    articles=[],
                ),
                user,
            )

        assert 'duplicate key value violates unique constraint "feeds_Feed_feed_url_unique"' in str(execinfo.value)

    def test_can_create_duplicated_feed_for_different_user(self, user):
        other_user = UserFactory()

        Feed.objects.create_from_metadata(
            FeedMetadata(
                feed_url=self.default_feed_url,
                site_url="https://example.com",
                title="Awesome website",
                description="A description",
                feed_type=SupportedFeedType.atom,
                etag="W/etag",
                last_modified=None,
                articles=[],
            ),
            other_user,
        )

        assert list(Feed.objects.values_list("feed_url", flat=True)) == [self.default_feed_url, self.default_feed_url]

    def test_disabled(self):
        Feed.objects.disable(self.feed, "Something went wrong")

        self.feed.refresh_from_db()
        assert not self.feed.enabled
        assert self.feed.disabled_reason == "We failed too many times to fetch the feed"
        feed_update = self.feed.feed_updates.last()
        assert not feed_update.success
        assert feed_update.error_message == "Something went wrong"

    def test_update_feed(self):
        Feed.objects.update_feed(
            self.feed,
            FeedMetadata(
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
        )

        assert self.feed.articles.count() == 1
        assert self.feed.feed_updates.count() == 1
