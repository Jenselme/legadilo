from datetime import UTC, datetime

import pytest
import time_machine
from asgiref.sync import async_to_sync
from django.db import IntegrityError

from legadilo.feeds.models import FeedArticle, FeedUpdate
from legadilo.feeds.tests.factories import (
    FeedCategoryFactory,
    FeedFactory,
    FeedUpdateFactory,
)
from legadilo.feeds.utils.feed_parsing import ArticleData, FeedData
from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory, TagFactory
from legadilo.users.tests.factories import UserFactory

from ... import constants as feeds_constants
from ...models import Feed


@pytest.mark.django_db()
class TestFeedQuerySet:
    def test_for_user(self, user, other_user):
        feed = FeedFactory(user=user)
        FeedFactory(user=other_user)

        feeds = Feed.objects.get_queryset().for_user(user)

        assert list(feeds) == [feed]

    @time_machine.travel("2024-05-08 11:00:00")
    def test_for_update(self, user):
        feed_updated_more_than_one_hour_ago = FeedFactory(
            title="Updated more than one hour ago",
            user=user,
            refresh_delay=feeds_constants.FeedRefreshDelays.HOURLY,
        )
        with time_machine.travel("2024-05-08 10:00:00"):
            FeedUpdateFactory(feed=feed_updated_more_than_one_hour_ago)
        disabled_feed_updated_more_than_one_hour_ago = FeedFactory(
            title="Disabled feed",
            user=user,
            refresh_delay=feeds_constants.FeedRefreshDelays.HOURLY,
            enabled=False,
        )
        with time_machine.travel("2024-05-08 10:00:00"):
            FeedUpdateFactory(feed=disabled_feed_updated_more_than_one_hour_ago)
        feed_updated_less_than_one_hour_ago = FeedFactory(
            title="Updated less than one hour ago",
            user=user,
            refresh_delay=feeds_constants.FeedRefreshDelays.HOURLY,
        )
        with time_machine.travel("2024-05-08 08:30:00"):
            FeedUpdateFactory(feed=feed_updated_less_than_one_hour_ago)
        with time_machine.travel("2024-05-08 10:30:00"):
            FeedUpdateFactory(feed=feed_updated_less_than_one_hour_ago)
        feed_updated_this_morning = FeedFactory(
            title="Updated this morning",
            user=user,
            refresh_delay=feeds_constants.FeedRefreshDelays.EVERY_MORNING,
        )
        with time_machine.travel("2024-05-07 10:00:00"):
            FeedUpdateFactory(feed=feed_updated_this_morning)
        with time_machine.travel("2024-05-08 10:00:00"):
            FeedUpdateFactory(feed=feed_updated_this_morning)
        feed_not_yet_updated_this_morning = FeedFactory(
            title="Not yet updated this morning",
            user=user,
            refresh_delay=feeds_constants.FeedRefreshDelays.EVERY_MORNING,
        )
        with time_machine.travel("2024-05-07 10:00:00"):
            FeedUpdateFactory(feed=feed_not_yet_updated_this_morning)

        feeds_to_update = Feed.objects.get_queryset().for_update()

        assert list(feeds_to_update) == [
            feed_updated_more_than_one_hour_ago,
            feed_not_yet_updated_this_morning,
        ]

    @time_machine.travel("2024-05-08 13:00:00")
    def test_for_update_not_morning(self, user):
        feed_updated_this_morning = FeedFactory(
            user=user, refresh_delay=feeds_constants.FeedRefreshDelays.EVERY_MORNING
        )
        with time_machine.travel("2024-05-08 10:00:00"):
            FeedUpdateFactory(feed=feed_updated_this_morning)
        feed_not_yet_updated_this_morning = FeedFactory(
            user=user, refresh_delay=feeds_constants.FeedRefreshDelays.EVERY_MORNING
        )
        with time_machine.travel("2024-05-07 10:00:00"):
            FeedUpdateFactory(feed=feed_not_yet_updated_this_morning)

        feeds_to_update = Feed.objects.get_queryset().for_update()

        assert list(feeds_to_update) == []

    def test_only_with_ids(self):
        feed1 = FeedFactory(enabled=True)
        feed2 = FeedFactory(enabled=True)

        feed_ids_to_update = (
            Feed.objects.get_queryset().only_with_ids().values_list("id", flat=True)
        )

        assert list(feed_ids_to_update) == [feed1.id, feed2.id]

        feed_ids_to_update = (
            Feed.objects.get_queryset()
            .only_with_ids([feed1.id])
            .values_list("id", flat=True)
            .order_by("id")
        )

        assert list(feed_ids_to_update) == [feed1.id]


@pytest.mark.django_db()
class TestFeedManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.default_feed_url = "https://example.com/feeds/atom.exsiting.xml"
        self.feed = FeedFactory(feed_url=self.default_feed_url, user=user)
        self.initial_feed_count = 1

    def test_get_feeds_by_categories_no_categories(self, other_user):
        feeds_by_categories = Feed.objects.get_by_categories(other_user)

        assert feeds_by_categories == {}

    def test_get_feeds_by_categories(self, user, other_user):
        feed_1_without_category = FeedFactory(user=user)
        feed_2_without_category = FeedFactory(user=user)
        feed_category = FeedCategoryFactory(user=user)
        feed_1_with_category = FeedFactory(
            user=user, title="Feed 1 with category", category=feed_category
        )
        feed_2_with_category = FeedFactory(
            user=user, title="Feed 2 with category", slug="", category=feed_category
        )
        other_feed_category = FeedCategoryFactory(user=user)
        feed_other_category = FeedFactory(user=user, category=other_feed_category)
        feed_category_other_user = FeedCategoryFactory(user=other_user)
        FeedFactory(user=other_user, category=feed_category_other_user, title="Feed other user")

        feeds_by_categories = Feed.objects.get_by_categories(user)

        assert feeds_by_categories == {
            None: [self.feed, feed_1_without_category, feed_2_without_category],
            feed_category.title: [feed_1_with_category, feed_2_with_category],
            other_feed_category.title: [feed_other_category],
        }

    def test_get_articles(self, user):
        article_of_feed = ArticleFactory(user=user)
        FeedArticle.objects.create(feed=self.feed, article=article_of_feed)
        other_feed = FeedFactory(user=user)
        article_of_other_feed = ArticleFactory(user=user)
        FeedArticle.objects.create(feed=other_feed, article=article_of_other_feed)

        articles_qs = Feed.objects.get_articles(self.feed)

        assert list(articles_qs) == [article_of_feed]

    def test_create_from_feed_data(self, user, django_assert_num_queries):
        with django_assert_num_queries(12):
            feed = Feed.objects.create_from_metadata(
                FeedData(
                    feed_url="https://example.com/feeds/atom.xml",
                    site_url="https://example.com",
                    title="Awesome website",
                    description="A description",
                    feed_type=feeds_constants.SupportedFeedType.atom,
                    etag="W/etag",
                    last_modified=None,
                    articles=[
                        ArticleData(
                            external_article_id="some-article-1",
                            title="Article 1",
                            summary="Summary 1",
                            content="Description 1",
                            authors=["Author"],
                            contributors=[],
                            tags=[],
                            link="https//example.com/article/1",
                            preview_picture_url="https://example.com/preview.png",
                            preview_picture_alt="Some image alt",
                            published_at=datetime.now(tz=UTC),
                            updated_at=datetime.now(tz=UTC),
                            source_title="Awesome website",
                            language="fr",
                        )
                    ],
                ),
                user,
                feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
                [],
            )

        assert Feed.objects.all().count() == self.initial_feed_count + 1
        assert feed.id > 0
        assert feed.tags.count() == 0
        assert feed.feed_url == "https://example.com/feeds/atom.xml"
        assert feed.site_url == "https://example.com"
        assert feed.title == "Awesome website"
        assert feed.slug == "awesome-website"
        assert feed.description == "A description"
        assert feed.feed_type == feeds_constants.SupportedFeedType.atom
        assert feed.articles.count() > 0
        feed_update = async_to_sync(FeedUpdate.objects.get_latest_success_for_feed)(feed)
        assert feed_update.status == feeds_constants.FeedUpdateStatus.SUCCESS
        assert not feed_update.error_message
        assert feed_update.feed_etag == "W/etag"
        assert feed_update.feed_last_modified is None
        assert Article.objects.count() > 0
        article = Article.objects.first()
        assert article is not None
        assert article.tags.count() == 0

    def test_create_from_metadata_with_tags(self, user, django_assert_num_queries):
        tag = TagFactory()

        with django_assert_num_queries(15):
            feed = Feed.objects.create_from_metadata(
                FeedData(
                    feed_url="https://example.com/feeds/atom.xml",
                    site_url="https://example.com",
                    title="Awesome website",
                    description="A description",
                    feed_type=feeds_constants.SupportedFeedType.atom,
                    etag="W/etag",
                    last_modified=None,
                    articles=[
                        ArticleData(
                            external_article_id="some-article-1",
                            title="Article 1",
                            summary="Summary 1",
                            content="Description 1",
                            authors=["Author"],
                            contributors=[],
                            tags=[],
                            link="https//example.com/article/1",
                            preview_picture_url="https://example.com/preview.png",
                            preview_picture_alt="Some image alt",
                            published_at=datetime.now(tz=UTC),
                            updated_at=datetime.now(tz=UTC),
                            source_title="Awesome website",
                            language="fr",
                        )
                    ],
                ),
                user,
                feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
                [tag],
            )

        assert Feed.objects.all().count() == self.initial_feed_count + 1
        assert feed.id > 0
        assert list(feed.tags.all()) == [tag]
        assert feed.feed_url == "https://example.com/feeds/atom.xml"
        assert feed.site_url == "https://example.com"
        assert feed.title == "Awesome website"
        assert feed.description == "A description"
        assert feed.feed_type == feeds_constants.SupportedFeedType.atom
        assert feed.articles.count() > 0
        feed_update = async_to_sync(FeedUpdate.objects.get_latest_success_for_feed)(feed)
        assert feed_update.status == feeds_constants.FeedUpdateStatus.SUCCESS
        assert not feed_update.error_message
        assert feed_update.feed_etag == "W/etag"
        assert feed_update.feed_last_modified is None
        assert Article.objects.count() > 0
        article = Article.objects.first()
        assert article is not None
        assert list(article.tags.all()) == [tag]

    def test_cannot_create_duplicated_feed_for_same_user(self, user):
        with pytest.raises(IntegrityError) as execinfo:
            Feed.objects.create_from_metadata(
                FeedData(
                    feed_url=self.default_feed_url,
                    site_url="https://example.com",
                    title="Awesome website",
                    description="A description",
                    feed_type=feeds_constants.SupportedFeedType.atom,
                    etag="W/etag",
                    last_modified=None,
                    articles=[],
                ),
                user,
                feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
                [],
            )

        assert 'duplicate key value violates unique constraint "feeds_feed_feed_url_unique"' in str(
            execinfo.value
        )

    def test_can_create_duplicated_feed_for_different_user(self, user):
        other_user = UserFactory()

        Feed.objects.create_from_metadata(
            FeedData(
                feed_url=self.default_feed_url,
                site_url="https://example.com",
                title="Awesome website",
                description="A description",
                feed_type=feeds_constants.SupportedFeedType.atom,
                etag="W/etag",
                last_modified=None,
                articles=[],
            ),
            other_user,
            feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
            [],
        )

        assert list(Feed.objects.values_list("feed_url", flat=True)) == [
            self.default_feed_url,
            self.default_feed_url,
        ]

    def test_disabled(self):
        Feed.objects.log_error(self.feed, "Something went wrong")

        self.feed.refresh_from_db()
        assert not self.feed.enabled
        assert self.feed.disabled_reason == "We failed too many times to fetch the feed"
        feed_update = self.feed.feed_updates.last()
        assert feed_update.status == feeds_constants.FeedUpdateStatus.FAILURE
        assert feed_update.error_message == "Something went wrong"

    def test_update_feed(self, django_assert_num_queries):
        existing_article = ArticleFactory(
            link="https://example.com/article/existing",
            initial_source_type=reading_constants.ArticleSourceType.MANUAL,
            initial_source_title="Not a feed",
            user=self.feed.user,
        )
        FeedArticle.objects.create(feed=self.feed, article=existing_article)

        with django_assert_num_queries(10):
            Feed.objects.update_feed(
                self.feed,
                FeedData(
                    feed_url="https://example.com/feeds/atom.xml",
                    site_url="https://example.com",
                    title="Awesome website",
                    description="A description",
                    feed_type=feeds_constants.SupportedFeedType.atom,
                    etag="W/etag",
                    last_modified=None,
                    articles=[
                        ArticleData(
                            external_article_id="some-article-1",
                            title="Article 1",
                            summary="Summary 1",
                            content="Description 1",
                            authors=["Author"],
                            contributors=[],
                            tags=[],
                            link="https//example.com/article/1",
                            preview_picture_url="https://example.com/preview.png",
                            preview_picture_alt="Some image alt",
                            published_at=datetime.now(tz=UTC),
                            updated_at=datetime.now(tz=UTC),
                            source_title=self.feed.title,
                            language="fr",
                        ),
                        ArticleData(
                            external_article_id="some-article-existing",
                            title="Article 2",
                            summary="Summary 2",
                            content="Description existing updated",
                            authors=["Author"],
                            contributors=[],
                            tags=[],
                            link=existing_article.link,
                            preview_picture_url="",
                            preview_picture_alt="",
                            published_at=datetime.now(tz=UTC),
                            updated_at=datetime.now(tz=UTC),
                            source_title=self.feed.title,
                            language="fr",
                        ),
                    ],
                ),
            )

        assert self.feed.articles.count() == 2
        assert self.feed.feed_updates.count() == 1
        new_article = self.feed.articles.exclude(id=existing_article.id).get()
        assert new_article.title == "Article 1"
        assert new_article.initial_source_type == reading_constants.ArticleSourceType.FEED
        assert new_article.initial_source_title == self.feed.title
        existing_article.refresh_from_db()
        assert existing_article.initial_source_type == reading_constants.ArticleSourceType.MANUAL
        assert existing_article.initial_source_title != self.feed.title
