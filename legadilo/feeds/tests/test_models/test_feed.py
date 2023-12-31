from datetime import UTC, datetime

import pytest
from asgiref.sync import sync_to_async
from django.db import IntegrityError

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.models import FeedUpdate
from legadilo.feeds.tests.factories import FeedFactory
from legadilo.feeds.utils.feed_parsing import FeedArticle, FeedMetadata
from legadilo.users.tests.factories import UserFactory
from legadilo.utils.iterables import alist

from ...models import Feed


@pytest.mark.django_db(transaction=True)
class TestFeedManager:
    @pytest.mark.asyncio()
    async def test_create_from_url(self, user, mocker):
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

        feed = await Feed.objects.create_from_url("https://example.com/feeds/atom.xml", user)

        assert await Feed.objects.all().acount() == 1
        assert feed.id > 0
        assert feed.feed_url == "https://example.com/feeds/atom.xml"
        assert feed.site_url == "https://example.com"
        assert feed.title == "Awesome website"
        assert feed.description == "A description"
        assert feed.feed_type == SupportedFeedType.atom
        assert await feed.articles.acount() > 0
        feed_update = await FeedUpdate.objects.get_latest_success_for_feed(feed)
        assert feed_update.success
        assert not feed_update.error_message
        assert feed_update.feed_etag == "W/etag"
        assert feed_update.feed_last_modified is None

    @pytest.mark.asyncio()
    async def test_cannot_create_duplicated_feed_for_same_user(self, user, mocker):
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
        await sync_to_async(FeedFactory)(feed_url="https://example.com/feeds/atom.xml", user=user)

        with pytest.raises(IntegrityError) as execinfo:
            await Feed.objects.create_from_url("https://example.com/feeds/atom.xml", user)

        assert 'duplicate key value violates unique constraint "feeds_Feed_feed_url_unique"' in str(execinfo.value)

    @pytest.mark.asyncio()
    async def test_can_create_duplicated_feed_for_different_user(self, user, mocker):
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
        other_user = await sync_to_async(UserFactory)()
        await sync_to_async(FeedFactory)(feed_url="https://example.com/feeds/atom.xml", user=other_user)

        await Feed.objects.create_from_url("https://example.com/feeds/atom.xml", user)

        assert await alist(Feed.objects.values_list("feed_url", flat=True)) == [
            "https://example.com/feeds/atom.xml",
            "https://example.com/feeds/atom.xml",
        ]
