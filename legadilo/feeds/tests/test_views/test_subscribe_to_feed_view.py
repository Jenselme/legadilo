# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
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

from http import HTTPStatus

import httpx
import pytest
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
from django.urls import reverse

from legadilo.feeds.models import Feed, FeedUpdate
from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedFactory
from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import TagFactory

from ... import constants as feeds_constants
from ..fixtures import get_feed_fixture_content, get_page_for_feed_subscription_content


@pytest.mark.django_db()
class TestSubscribeToFeedView:
    @pytest.fixture()
    def sample_rss_feed(self):
        return get_feed_fixture_content("sample_rss.xml")

    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("feeds:subscribe_to_feed")
        self.feed_url = "https://example.com/feeds/atom.xml"
        self.sample_payload = {
            "url": self.feed_url,
            "refresh_delay": feeds_constants.FeedRefreshDelays.BIHOURLY.name,
            "open_original_link_by_default": True,
        }
        self.existing_tag = TagFactory(user=user)
        self.sample_payload_with_tags = {
            "url": self.feed_url,
            "refresh_delay": feeds_constants.FeedRefreshDelays.DAILY_AT_NOON.name,
            "tags": [self.existing_tag.slug, "New"],
        }
        self.page_url = "https://example.com"
        self.sample_page_payload = {
            "url": self.page_url,
            "refresh_delay": feeds_constants.FeedRefreshDelays.DAILY_AT_NOON.name,
        }

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_form(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK

    def test_subscribe_to_feed(
        self, logged_in_sync_client, httpx_mock, django_assert_num_queries, sample_rss_feed
    ):
        httpx_mock.add_response(text=sample_rss_feed, url=self.feed_url)

        with django_assert_num_queries(29):
            response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        feed = Feed.objects.get()
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message=f"Feed '<a href=\"/feeds/articles/{feed.id}/\">Sample Feed</a>' added",
            )
        ]
        assert feed.tags.count() == 0
        assert feed.open_original_link_by_default
        assert Article.objects.count() > 0
        article = Article.objects.first()
        assert article is not None
        assert article.tags.count() == 0
        assert FeedUpdate.objects.count() == 1

    def test_subscribe_to_feed_with_tags(
        self, logged_in_sync_client, httpx_mock, django_assert_num_queries, sample_rss_feed
    ):
        httpx_mock.add_response(text=sample_rss_feed, url=self.feed_url)

        with django_assert_num_queries(34):
            response = logged_in_sync_client.post(self.url, self.sample_payload_with_tags)

        assert response.status_code == HTTPStatus.CREATED, response.context["form"].errors
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        feed = Feed.objects.get()
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message=f"Feed '<a href=\"/feeds/articles/{feed.id}/\">Sample Feed</a>' added",
            )
        ]
        assert not feed.open_original_link_by_default
        assert list(feed.tags.values_list("slug", flat=True)) == ["new", self.existing_tag.slug]
        assert Article.objects.count() > 0
        article = Article.objects.first()
        assert article is not None
        assert list(article.article_tags.values_list("tag__slug", "tagging_reason")) == [
            ("new", reading_constants.TaggingReason.FROM_FEED),
            (self.existing_tag.slug, reading_constants.TaggingReason.FROM_FEED),
        ]
        assert FeedUpdate.objects.count() == 1

    def test_subscribe_to_feed_with_category(
        self, logged_in_sync_client, httpx_mock, django_assert_num_queries, sample_rss_feed, user
    ):
        category = FeedCategoryFactory(user=user)
        sample_payload_with_category = {
            "url": self.feed_url,
            "refresh_delay": feeds_constants.FeedRefreshDelays.DAILY_AT_NOON.name,
            "category": category.slug,
        }
        httpx_mock.add_response(text=sample_rss_feed, url=self.feed_url)

        with django_assert_num_queries(29):
            response = logged_in_sync_client.post(self.url, sample_payload_with_category)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        feed = Feed.objects.get()
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message=f"Feed '<a href=\"/feeds/articles/{feed.id}/\">Sample Feed</a>' added",
            )
        ]
        assert Feed.objects.count() == 1
        assert feed.tags.count() == 0
        assert feed.category == category
        assert Article.objects.count() > 0
        article = Article.objects.first()
        assert article is not None
        assert article.tags.count() == 0
        assert FeedUpdate.objects.count() == 1

    def test_subscribe_to_feed_from_feed_choices(
        self, logged_in_sync_client, httpx_mock, sample_rss_feed
    ):
        httpx_mock.add_response(text=sample_rss_feed, url=self.feed_url)

        response = logged_in_sync_client.post(
            self.url,
            {
                "url": self.page_url,
                "proposed_feed_choices": f'[["{self.feed_url}", "Cat 1 feed"], '
                '["https://www.jujens.eu/feeds/all.rss.xml", "Full feed"]]',
                "feed_choices": self.feed_url,
                "refresh_delay": feeds_constants.FeedRefreshDelays.DAILY_AT_NOON.name,
            },
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        feed = Feed.objects.get()
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message=f"Feed '<a href=\"/feeds/articles/{feed.id}/\">Sample Feed</a>' added",
            )
        ]
        assert FeedUpdate.objects.count() == 1

    def test_invalid_form(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, {"url": "toto"})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "feeds/subscribe_to_feed.html"

    def test_fetch_failure(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("Unable to read within timeout"))

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="Failed to fetch the feed. Please check that the URL you entered is "
                "correct, that the feed exists and is accessible.",
            )
        ]

    def test_fetched_file_too_big(self, logged_in_sync_client, httpx_mock, mocker, sample_rss_feed):
        mocker.patch(
            "legadilo.feeds.services.feed_parsing.sys.getsizeof", return_value=11 * 1024 * 1024
        )
        httpx_mock.add_response(text=sample_rss_feed, url=self.feed_url)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="The feed file is too big, we won't parse it. "
                "Try to find a more lightweight feed.",
            )
        ]

    def test_fetched_file_invalid_feed(self, logged_in_sync_client, httpx_mock):
        sample_rss_feed = get_feed_fixture_content(
            "sample_rss.xml", {"item_link": """<link>Just trash</link>"""}
        )
        httpx_mock.add_response(
            text=sample_rss_feed,
            url=self.feed_url,
        )

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        assert response.template_name == "feeds/subscribe_to_feed.html"
        assert Article.objects.count() == 0

    def test_duplicated_feed(self, user, logged_in_sync_client, httpx_mock, sample_rss_feed):
        FeedFactory(feed_url=self.feed_url, user=user)
        httpx_mock.add_response(text=sample_rss_feed, url=self.feed_url)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="You are already subscribed to this feed.",
            )
        ]

    def test_cannot_find_feed_url(self, logged_in_sync_client, httpx_mock):
        sample_html_template = get_page_for_feed_subscription_content({"feed_links": ""})
        httpx_mock.add_response(text=sample_html_template, url=self.page_url)

        response = logged_in_sync_client.post(self.url, self.sample_page_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="Failed to find a feed URL on the supplied page.",
            )
        ]

    def test_multiple_feed_urls_found(self, logged_in_sync_client, httpx_mock):
        sample_html_template = get_page_for_feed_subscription_content({
            "feed_links": """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.atom.xml" type="application/atom+xml" rel="alternate" title="Cat 1 feed">"""  # noqa: E501
        })
        httpx_mock.add_response(
            text=sample_html_template,
            url=self.page_url,
        )

        response = logged_in_sync_client.post(self.url, self.sample_page_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "feeds/subscribe_to_feed.html"
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["WARNING"],
                message="Multiple feeds were found at this location, please select the proper one.",
            )
        ]
        form = response.context_data["form"]
        assert form.fields["url"].widget.attrs["readonly"] == "true"
        assert form.initial == {
            "proposed_feed_choices": '[["https://www.jujens.eu/feeds/cat1.atom.xml", "Cat 1 feed"],'
            ' ["https://www.jujens.eu/feeds/all.rss.xml", "Full feed"]]'
        }
        assert form.fields["feed_choices"].required
        assert form.fields["feed_choices"].choices == [
            ("https://www.jujens.eu/feeds/cat1.atom.xml", "Cat 1 feed"),
            ("https://www.jujens.eu/feeds/all.rss.xml", "Full feed"),
        ]

    def test_other_user_subscribe_to_same_feed(
        self, user, other_user, logged_in_other_user_sync_client, httpx_mock, sample_rss_feed
    ):
        FeedFactory(feed_url=self.feed_url, user=user)
        wrong_category = FeedCategoryFactory(user=user)
        category = FeedCategoryFactory(
            user=other_user, title=wrong_category.title, slug=wrong_category.slug
        )
        existing_tag = TagFactory(
            user=other_user, title=self.existing_tag.title, slug=self.existing_tag.slug
        )
        assert category.slug == wrong_category.slug
        assert existing_tag.slug == self.existing_tag.slug
        httpx_mock.add_response(text=sample_rss_feed, url=self.feed_url)
        payload = {
            "url": self.feed_url,
            "refresh_delay": feeds_constants.FeedRefreshDelays.DAILY_AT_NOON.name,
            "category": category.slug,
            "tags": [existing_tag.slug, "New"],
        }

        response = logged_in_other_user_sync_client.post(self.url, payload)

        assert response.status_code == HTTPStatus.CREATED
        feed = Feed.objects.exclude(user=user).first()
        assert feed is not None
        assert feed.user == other_user
        assert feed.tags.count() == 2
        assert set(feed.tags.values_list("user_id", flat=True)) == {other_user.id}
        assert feed.category == category
        assert category.user == other_user
        assert Article.objects.count() == Article.objects.filter(user=other_user).count()
        article = Article.objects.first()
        assert article is not None
        assert article.tags.count() == 2
        assert set(article.tags.values_list("user_id", flat=True)) == {other_user.id}
