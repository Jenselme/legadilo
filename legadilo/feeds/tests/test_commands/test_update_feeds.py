import pytest
from django.core.management import call_command

from legadilo.feeds.models import Article
from legadilo.feeds.tests.factories import FeedFactory

from ..fixtures import SAMPLE_RSS_FEED


@pytest.mark.django_db(transaction=True)
class TestUpdateFeedsCommand:
    def test_update_feed_command_no_feed(self):
        call_command("update_feeds")

    def test_update_feed_command(self, httpx_mock):
        feed_url = "http://example.com/feed/rss.xml"
        FeedFactory(feed_url=feed_url)
        httpx_mock.add_response(url=feed_url, content=SAMPLE_RSS_FEED)

        call_command("update_feeds")

        assert Article.objects.count() == 1
