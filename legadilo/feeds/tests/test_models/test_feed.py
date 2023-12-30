import pytest
from asgiref.sync import sync_to_async
from django.db import IntegrityError

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.tests.factories import FeedFactory
from legadilo.feeds.utils.feed_parsing import FeedMetadata
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
            ),
            autospec=True,
        )

        obj = await Feed.objects.create_from_url("https://example.com/feeds/atom.xml", user)

        assert await Feed.objects.all().acount() == 1
        assert obj.id > 0
        assert obj.feed_url == "https://example.com/feeds/atom.xml"
        assert obj.site_url == "https://example.com"
        assert obj.title == "Awesome website"
        assert obj.description == "A description"
        assert obj.feed_type == SupportedFeedType.atom

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
