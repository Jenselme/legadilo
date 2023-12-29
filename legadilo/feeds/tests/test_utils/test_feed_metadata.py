import pytest

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.utils.feed_metadata import (
    FeedMetadata,
    MultipleFeedFoundError,
    NoFeedUrlFoundError,
    find_feed_page_content,
    get_feed_metadata,
)

from ..fixtures import SAMPLE_ATOM_FEED, SAMPLE_HTML_TEMPLATE, SAMPLE_RSS_FEED


class TestFindFeedUrl:
    @pytest.mark.parametrize(
        ("content", "expected_link"),
        [
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link href="https://www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",  # noqa: E501
                ),
                "https://www.jujens.eu/feeds/all.rss.xml",
                id="single-rss-link",
            ),
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link href="https://www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
                ),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="single-atom-link",
            ),
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link href="https://www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">
                    <link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
                ),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="duplicate-link",
            ),
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">>""",  # noqa: E501
                ),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="link-no-scheme",
            ),
        ],
    )
    def test_find_one_link(self, content, expected_link):
        link = find_feed_page_content(content)

        assert link == expected_link

    @pytest.mark.parametrize(
        "content",
        [
            pytest.param("", id="empty-string"),
            pytest.param("<head></head", id="bad-html"),
            pytest.param(SAMPLE_HTML_TEMPLATE.replace("{{PLACEHOLDER}}", ""), id="no-links"),
            pytest.param(SAMPLE_HTML_TEMPLATE.replace("{{PLACEHOLDER}}", "invalid data"), id="invalid-data-in-head"),
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",
                ),
                id="no-href",
            ),
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link href="" type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",
                ),
                id="empty-href",
            ),
        ],
    )
    def test_cannot_find_feed_url(self, content):
        with pytest.raises(NoFeedUrlFoundError):
            find_feed_page_content(content)

    @pytest.mark.parametrize(
        ("content", "expected_urls"),
        [
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.rss.xml" type="application/rss+xml" rel="alternate" title="Cat 1 feed">""",  # noqa: E501
                ),
                {"https://www.jujens.eu/feeds/all.rss.xml", "https://www.jujens.eu/feeds/cat1.rss.xml"},
                id="multiple-rss-links",
            ),
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.atom.xml" type="application/atom+xml" rel="alternate" title="Cat 1 feed">""",  # noqa: E501
                ),
                {"https://www.jujens.eu/feeds/all.atom.xml", "https://www.jujens.eu/feeds/cat1.atom.xml"},
                id="multiple-atom-links",
            ),
            pytest.param(
                SAMPLE_HTML_TEMPLATE.replace(
                    "{{PLACEHOLDER}}",
                    """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.atom.xml" type="application/atom+xml" rel="alternate" title="Cat 1 feed">""",  # noqa: E501
                ),
                {"https://www.jujens.eu/feeds/all.rss.xml", "https://www.jujens.eu/feeds/cat1.atom.xml"},
                id="various-types",
            ),
        ],
    )
    def test_find_multiple_url(self, content, expected_urls):
        with pytest.raises(MultipleFeedFoundError) as excinfo:
            find_feed_page_content(content)

        assert excinfo.value.feed_urls == expected_urls


class TestGetFeedMetadata:
    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("feed_url", "feed_content", "feed_type"),
        [
            pytest.param(
                "https://www.jujens.eu/feed/rss.xml", SAMPLE_RSS_FEED, SupportedFeedType.rss20, id="sample-rss-feed"
            ),
            pytest.param(
                "https://www.jujens.eu/feed/atom.xml",
                SAMPLE_ATOM_FEED,
                SupportedFeedType.atom10,
                id="sample-atom-feed",
            ),
        ],
    )
    async def test_get_feed_metadata_from_feed_url(self, feed_url, feed_content, feed_type, httpx_mock):
        httpx_mock.add_response(text=feed_content, url=feed_url)

        metadata = await get_feed_metadata(feed_url)

        assert metadata == FeedMetadata(
            feed_url=feed_url,
            site_url="http://example.org/",
            title="Sample Feed",
            description="For documentation only",
            feed_type=feed_type,
        )

    @pytest.mark.asyncio()
    async def test_get_feed_metadata_from_page_url(self, httpx_mock):
        page_content = SAMPLE_HTML_TEMPLATE.replace(
            "{{PLACEHOLDER}}",
            """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
        )
        page_url = "https://www.jujens.eu"
        feed_url = "https://www.jujens.eu/feeds/all.atom.xml"
        httpx_mock.add_response(text=page_content, url=page_url)
        httpx_mock.add_response(text=SAMPLE_ATOM_FEED, url=feed_url)

        metadata = await get_feed_metadata(page_url)

        assert metadata == FeedMetadata(
            feed_url=feed_url,
            site_url="http://example.org/",
            title="Sample Feed",
            description="For documentation only",
            feed_type=SupportedFeedType.atom10,
        )
