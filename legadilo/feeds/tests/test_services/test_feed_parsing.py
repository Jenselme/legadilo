# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import httpx
import pytest

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.services.feed_parsing import (
    FeedFileTooBigError,
    MultipleFeedFoundError,
    NoFeedUrlFoundError,
    _find_feed_page_content,
    _find_youtube_rss_feed_url,
    _get_feed_site_url,
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
        ("content", "expected_url"),
        [
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_urls": """<link href="https://www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",  # noqa: E501
                }),
                "https://www.jujens.eu/feeds/all.rss.xml",
                id="single-rss-link",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_urls": """<link href="https://www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
                }),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="single-atom-link",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_urls": """<link href="https://www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">
                    <link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
                }),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="duplicate-link",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_urls": """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">>""",  # noqa: E501
                }),
                "https://www.jujens.eu/feeds/all.atom.xml",
                id="link-no-scheme",
            ),
        ],
    )
    def test_find_one_url(self, content: str, expected_url: str):
        url = _find_feed_page_content(content)

        assert url == expected_url

    @pytest.mark.parametrize(
        "content",
        [
            pytest.param("", id="empty-string"),
            pytest.param("<head></head", id="bad-html"),
            pytest.param(get_page_for_feed_subscription_content({"feed_urls": ""}), id="no-links"),
            pytest.param(
                get_page_for_feed_subscription_content({"feed_urls": "invalid data"}),
                id="invalid-data-in-head",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_urls": """<link type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",  # noqa: E501
                }),
                id="no-href",
            ),
            pytest.param(
                get_page_for_feed_subscription_content({
                    "feed_urls": """<link href="" type="application/rss+xml" rel="alternate" title="Jujens' blog RSS">""",  # noqa: E501
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
                    "feed_urls": """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
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
                    "feed_urls": """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Full feed">
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
                    "feed_urls": """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
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
                    "feed_urls": """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate">
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
    def test_get_feed_metadata_from_feed_url(
        self, feed_url: str, feed_content: str, feed_type: SupportedFeedType, httpx_mock, snapshot
    ):
        httpx_mock.add_response(text=feed_content, url=feed_url)

        with httpx.Client() as client:
            feed_data = get_feed_data(feed_url, client=client)

        assert feed_data.feed_url == feed_url
        assert feed_data.feed_type == feed_type
        snapshot.assert_match(serialize_for_snapshot(feed_data), "feed_data.json")

    @pytest.mark.parametrize(
        ("user_entered_url", "expected_url"),
        [
            pytest.param(
                "https://www.youtube.com/feeds/videos.xml?channel_id=toto",
                "https://www.youtube.com/feeds/videos.xml?channel_id=toto",
                id="already-is-channel-feed-link",
            ),
            pytest.param(
                "https://www.youtube.com/feeds/videos.xml?playlist_id=toto",
                "https://www.youtube.com/feeds/videos.xml?playlist_id=toto",
                id="already-is-playlist-feed-link",
            ),
            pytest.param(
                "https://www.youtube.com/channel/toto",
                "https://www.youtube.com/feeds/videos.xml?channel_id=toto",
                id="is-channel-with-id",
            ),
            pytest.param(
                "https://www.youtube.com/watch?v=video_id&list=toto",
                "https://www.youtube.com/feeds/videos.xml?playlist_id=toto",
                id="is-playlist-url",
            ),
            pytest.param(
                "https://www.youtube.com/watch?v=someVideo",
                "https://www.youtube.com/watch?v=someVideo",
                id="some-other-youtube-url",
            ),
        ],
    )
    def test_find_youtube_rss_feed_url(self, user_entered_url: str, expected_url: str):
        youtube_feed_url = _find_youtube_rss_feed_url(user_entered_url)

        assert youtube_feed_url == expected_url

    def test_get_feed_metadata_from_page_url(self, httpx_mock, snapshot):
        page_content = get_page_for_feed_subscription_content({
            "feed_urls": """<link href="//www.jujens.eu/feeds/all.atom.xml" type="application/atom+xml" rel="alternate" title="Jujens' blog Atom">""",  # noqa: E501
        })
        page_url = "https://www.jujens.eu"
        feed_url = "https://www.jujens.eu/feeds/all.atom.xml"
        httpx_mock.add_response(text=page_content, url=page_url)
        httpx_mock.add_response(text=get_feed_fixture_content("sample_atom.xml"), url=feed_url)

        with httpx.Client() as client:
            feed_data = get_feed_data(page_url, client=client)

        assert feed_data.feed_type == SupportedFeedType.atom10
        snapshot.assert_match(serialize_for_snapshot(feed_data), "feed_data.json")

    def test_feed_file_too_big(self, httpx_mock, mocker):
        mocker.patch(
            "legadilo.feeds.services.feed_parsing.sys.getsizeof", return_value=11 * 1024 * 1024
        )
        httpx_mock.add_response(
            text=get_feed_fixture_content("sample_atom.xml"),
            url="https://www.jujens.eu/feed/rss.xml",
        )

        with pytest.raises(FeedFileTooBigError), httpx.Client() as client:
            get_feed_data("https://www.jujens.eu/feed/rss.xml", client=client)

    def test_feed_file_is_an_attack(self, httpx_mock, snapshot):
        feed_url = "https://example.com/feed.xml"
        httpx_mock.add_response(text=get_feed_fixture_content("attack_feed.xml"), url=feed_url)

        with httpx.Client() as client:
            feed_data = get_feed_data(feed_url, client=client)

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


class TestGetFeedSiteUrl:
    @pytest.mark.parametrize(
        ("found_site_url", "feed_url", "expected_site_url"),
        [
            pytest.param(
                None,
                "https://example.com/feed.xml",
                "https://example.com",
                id="failed-to-find-feed",
            ),
            pytest.param(
                "https://example.fr/the-site/",
                "https://example.com/feed.xml",
                "https://example.fr/the-site/",
                id="found-in-full",
            ),
            pytest.param(
                "//example.com",
                "https://example.com/feed.xml",
                "https://example.com",
                id="found-without-scheme-full",
            ),
            pytest.param(
                "/", "https://example.com/feed.xml", "https://example.com", id="not-full-url"
            ),
        ],
    )
    def test_get_feed_site_url(
        self, found_site_url: str | None, feed_url: str, expected_site_url: str
    ):
        build_site_url = _get_feed_site_url(found_site_url, feed_url)

        assert build_site_url == expected_site_url
