import httpx
import pytest

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.utils.feed_parsing import (
    FeedFileTooBigError,
    MultipleFeedFoundError,
    NoFeedUrlFoundError,
    _find_feed_page_content,
    _parse_articles_in_feed,
    get_feed_data,
    parse_feed,
)
from legadilo.utils.testing import serialize_for_snapshot

from ..fixtures import (
    get_feed_fixture_content,
    get_page_for_feed_subscription_content,
)


class TestFindFeedUrl:
    @pytest.mark.parametrize(
        ("content", "expected_link"),
        [
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="https://www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",  # noqa: E501
                }),
                "https://www.jujens.eu/feeds/all.rss.xml",
                id="single-rss-link",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="https://www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
                }),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="single-atom-link",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="https://www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">
                    <link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
                }),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="duplicate-link",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">>""",  # noqa: E501
                }),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="link-no-scheme",
            ),
        ],
    )
    def test_find_one_link(self, content: str, expected_link: str):
        link = _find_feed_page_content(content)

        assert link == expected_link

    @pytest.mark.parametrize(
        "content",
        [
            pytest.param("", id="empty-string"),
            pytest.param("<head></head", id="bad-html"),
            pytest.param(get_page_for_feed_subscription_content({"feed_links": ""}), id="no-links"),
            pytest.param(
                get_page_for_feed_subscription_content({"feed_links": "invalid data"}),
                id="invalid-data-in-head",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",  # noqa: E501
                }),
                id="no-href",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="" type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",  # noqa: E501
                }),
                id="empty-href",
            ),
        ],
    )
    def test_cannot_find_feed_url(self, content):
        with pytest.raises(NoFeedUrlFoundError):
            _find_feed_page_content(content)

    @pytest.mark.parametrize(
        ("content", "expected_urls"),
        [
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.rss.xml" type="application/rss+xml" rel="alternate" title="Cat 1 feed">""",  # noqa: E501
                }),
                [
                    ("https://www.jujens.eu/feeds/all.rss.xml", "Full feed"),
                    ("https://www.jujens.eu/feeds/cat1.rss.xml", "Cat 1 feed"),
                ],
                id="multiple-rss-links",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.atom.xml" type="application/atom+xml" rel="alternate" title="Cat 1 feed">""",  # noqa: E501
                }),
                [
                    ("https://www.jujens.eu/feeds/all.atom.xml", "Full feed"),
                    ("https://www.jujens.eu/feeds/cat1.atom.xml", "Cat 1 feed"),
                ],
                id="multiple-atom-links",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.atom.xml" type="application/atom+xml" rel="alternate" title="Cat 1 feed">""",  # noqa: E501
                }),
                [
                    ("https://www.jujens.eu/feeds/cat1.atom.xml", "Cat 1 feed"),
                    ("https://www.jujens.eu/feeds/all.rss.xml", "Full feed"),
                ],
                id="various-types",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_links": """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate">
                    <link href="//www.jujens.eu/feeds/cat1.atom.xml" type="application/atom+xml" rel="alternate" title="">""",  # noqa: E501
                }),
                [
                    (
                        "https://www.jujens.eu/feeds/cat1.atom.xml",
                        "https://www.jujens.eu/feeds/cat1.atom.xml",
                    ),
                    (
                        "https://www.jujens.eu/feeds/all.rss.xml",
                        "https://www.jujens.eu/feeds/all.rss.xml",
                    ),
                ],
                id="missing-titles",
            ),
        ],
    )
    def test_find_multiple_url(self, content, expected_urls):
        with pytest.raises(MultipleFeedFoundError) as excinfo:
            _find_feed_page_content(content)

        assert excinfo.value.feed_urls == expected_urls


class TestGetFeedMetadata:
    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("feed_url", "feed_content", "feed_type"),
        [
            pytest.param(
                "https://www.jujens.eu/feed/rss.xml",
                get_feed_fixture_content("sample_rss.xml"),
                SupportedFeedType.rss20,
                id="sample-rss-feed",
            ),
            pytest.param(
                "https://www.jujens.eu/feed/atom.xml",
                get_feed_fixture_content("sample_atom.xml"),
                SupportedFeedType.atom10,
                id="sample-atom-feed",
            ),
        ],
    )
    async def test_get_feed_metadata_from_feed_url(
        self, feed_url: str, feed_content: str, feed_type: SupportedFeedType, httpx_mock, snapshot
    ):
        httpx_mock.add_response(text=feed_content, url=feed_url)

        async with httpx.AsyncClient() as client:
            feed_data = await get_feed_data(feed_url, client=client)

        assert feed_data.feed_url == feed_url
        assert feed_data.feed_type == feed_type
        snapshot.assert_match(serialize_for_snapshot(feed_data), "feed_data.json")

    @pytest.mark.asyncio()
    async def test_get_feed_metadata_from_page_url(self, httpx_mock, snapshot):
        page_content = get_page_for_feed_subscription_content({
            "feed_links": """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
        })
        page_url = "https://www.jujens.eu"
        feed_url = "https://www.jujens.eu/feeds/all.atom.xml"
        httpx_mock.add_response(text=page_content, url=page_url)
        httpx_mock.add_response(text=get_feed_fixture_content("sample_atom.xml"), url=feed_url)

        async with httpx.AsyncClient() as client:
            feed_data = await get_feed_data(page_url, client=client)

        assert feed_data.feed_type == SupportedFeedType.atom10
        snapshot.assert_match(serialize_for_snapshot(feed_data), "feed_data.json")

    @pytest.mark.asyncio()
    async def test_feed_file_too_big(self, httpx_mock, mocker):
        mocker.patch("legadilo.feeds.utils.feed_parsing.sys.getsizeof", return_value=2048 * 1024)
        httpx_mock.add_response(
            text=get_feed_fixture_content("sample_atom.xml"),
            url="https://www.jujens.eu/feed/rss.xml",
        )

        with pytest.raises(FeedFileTooBigError):
            async with httpx.AsyncClient() as client:
                await get_feed_data("https://www.jujens.eu/feed/rss.xml", client=client)

    @pytest.mark.asyncio()
    async def test_feed_file_is_an_attack(self, httpx_mock, snapshot):
        feed_url = "https://example.com/feed.xml"
        httpx_mock.add_response(text=get_feed_fixture_content("attack_feed.xml"), url=feed_url)

        async with httpx.AsyncClient() as client:
            feed_data = await get_feed_data(feed_url, client=client)

        snapshot.assert_match(serialize_for_snapshot(feed_data), "feed_data.json")


class TestParseArticlesInFeed:
    @pytest.mark.parametrize(
        "feed_content",
        [
            pytest.param(
                get_feed_fixture_content("sample_rss.xml"),
                id="sample-rss-feed",
            ),
            pytest.param(
                get_feed_fixture_content("sample_atom.xml"),
                id="sample-atom-feed",
            ),
            pytest.param(
                get_feed_fixture_content(
                    "sample_atom.xml",
                    {"media_content_variant": "media_content_description"},  # type: ignore[arg-type]
                ),
                id="atom-with-media-description",
            ),
            pytest.param(
                get_feed_fixture_content(
                    "sample_atom.xml",
                    {"media_content_variant": "media_content_title"},  # type: ignore[arg-type]
                ),
                id="atom-with-media-title",
            ),
            pytest.param(
                get_feed_fixture_content("sample_youtube_atom.xml"),
                id="atom-from-youtube",
            ),
        ],
    )
    def test_parse_articles(self, feed_content, snapshot):
        feed_data = parse_feed(feed_content)

        articles = _parse_articles_in_feed(
            "https://example.com/feeds/feed.xml", "Some feed", feed_data
        )

        snapshot.assert_match(serialize_for_snapshot(articles), "articles.json")
