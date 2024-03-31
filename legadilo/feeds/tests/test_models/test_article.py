from datetime import UTC, datetime
from typing import Any

import pytest
import time_machine
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models

from legadilo.feeds import constants
from legadilo.feeds.models import Article, ArticleTag, ReadingList, ReadingListTag
from legadilo.feeds.tests.factories import (
    ArticleFactory,
    FeedFactory,
    ReadingListFactory,
    TagFactory,
)
from legadilo.feeds.utils.feed_parsing import FeedArticle


class TestArticleQuerySet:
    @pytest.mark.parametrize(
        ("reading_list_kwargs", "expected_filter"),
        [
            pytest.param(
                {"read_status": constants.ReadStatus.ONLY_UNREAD},
                models.Q(is_read=False),
                id="unread_only",
            ),
            pytest.param(
                {"read_status": constants.ReadStatus.ONLY_READ},
                models.Q(is_read=True),
                id="read_only",
            ),
            pytest.param(
                {"favorite_status": constants.FavoriteStatus.ONLY_NON_FAVORITE},
                models.Q(is_favorite=False),
                id="non_favorite_only",
            ),
            pytest.param(
                {"favorite_status": constants.FavoriteStatus.ONLY_FAVORITE},
                models.Q(is_favorite=True),
                id="favorite_only",
            ),
            pytest.param(
                {
                    "articles_max_age_unit": constants.ArticlesMaxAgeUnit.HOURS,
                    "articles_max_age_value": 1,
                },
                models.Q(published_at__gt=datetime(2024, 3, 19, 20, 8, 0, tzinfo=UTC)),
                id="max_age_hours",
            ),
            pytest.param(
                {
                    "articles_max_age_unit": constants.ArticlesMaxAgeUnit.DAYS,
                    "articles_max_age_value": 1,
                },
                models.Q(published_at__gt=datetime(2024, 3, 18, 21, 8, 0, tzinfo=UTC)),
                id="max_age_days",
            ),
            pytest.param(
                {
                    "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS,
                    "articles_max_age_value": 1,
                },
                models.Q(published_at__gt=datetime(2024, 3, 12, 21, 8, 0, tzinfo=UTC)),
                id="max_age_weeks",
            ),
            pytest.param(
                {
                    "articles_max_age_unit": constants.ArticlesMaxAgeUnit.MONTHS,
                    "articles_max_age_value": 1,
                },
                models.Q(published_at__gt=datetime(2024, 2, 19, 21, 8, 0, tzinfo=UTC)),
                id="max_age_months",
            ),
            pytest.param(
                {
                    "read_status": constants.ReadStatus.ONLY_UNREAD,
                    "favorite_status": constants.FavoriteStatus.ONLY_FAVORITE,
                },
                models.Q(is_read=False) & models.Q(is_favorite=True),
                id="simple-combination",
            ),
            pytest.param(
                {
                    "read_status": constants.ReadStatus.ONLY_UNREAD,
                    "favorite_status": constants.FavoriteStatus.ONLY_FAVORITE,
                    "articles_max_age_unit": constants.ArticlesMaxAgeUnit.MONTHS,
                    "articles_max_age_value": 1,
                },
                models.Q(is_read=False)
                & models.Q(is_favorite=True)
                & models.Q(
                    published_at__gt=datetime(2024, 2, 19, 21, 8, 0, tzinfo=UTC),
                ),
                id="full-combination",
            ),
        ],
    )
    def test_build_filters_from_reading_list(
        self, user, reading_list_kwargs: dict[str, Any], expected_filter: models.Q
    ):
        reading_list = ReadingListFactory(**reading_list_kwargs, user=user)

        with time_machine.travel("2024-03-19 21:08:00"):
            filters = Article.objects.get_queryset().build_filters_from_reading_list(reading_list)

        assert filters == models.Q(feed__user=user) & expected_filter

    def test_for_reading_list_with_tags(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(user=user)
        feed = FeedFactory(user=user)
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        ReadingListTag.objects.create(reading_list=reading_list, tag=tag1)
        # Article 1 is linked to all tags.
        article1 = ArticleFactory(feed=feed)
        ArticleTag.objects.create(
            article=article1, tag=tag1, tagging_reason=constants.TaggingReason.FROM_FEED
        )
        ArticleTag.objects.create(
            article=article1, tag=tag2, tagging_reason=constants.TaggingReason.FROM_FEED
        )
        # Article 2 is linked only to the tag of the reading list.
        article2 = ArticleFactory(feed=feed)
        ArticleTag.objects.create(
            article=article2, tag=tag1, tagging_reason=constants.TaggingReason.ADDED_MANUALLY
        )
        # Article 3 is only linked to the other tag.
        article3 = ArticleFactory(feed=feed)
        ArticleTag.objects.create(
            article=article3, tag=tag2, tagging_reason=constants.TaggingReason.ADDED_MANUALLY
        )
        # Article 4 is linked to the tag of the reading list but the tag is marked as deleted.
        article4 = ArticleFactory(feed=feed)
        ArticleTag.objects.create(
            article=article4, tag=tag1, tagging_reason=constants.TaggingReason.DELETED
        )

        with django_assert_num_queries(1):
            articles_paginator = Article.objects.get_articles_of_reading_list(reading_list)

        assert articles_paginator.num_pages == 1
        assert articles_paginator.count == 2
        articles_page = articles_paginator.page(1)
        assert list(articles_page.object_list) == [article1, article2]


@pytest.mark.django_db()
class TestArticleManager:
    def test_update_and_create_articles(self, django_assert_num_queries):
        feed = FeedFactory()
        tag1 = TagFactory(user=feed.user)
        tag2 = TagFactory(user=feed.user)
        feed.tags.add(tag1, tag2)
        existing_article = ArticleFactory(
            feed=feed, article_feed_id=f"existing-article-feed-{feed.id}"
        )

        with django_assert_num_queries(3):
            Article.objects.update_or_create_from_articles_list(
                [
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
                    ),
                    FeedArticle(
                        article_feed_id=existing_article.article_feed_id,
                        title="Article updated",
                        summary="Summary updated",
                        content="Description updated",
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        link="https//example.com/article/updated",
                        published_at=datetime.now(tz=UTC),
                        updated_at=datetime.now(tz=UTC),
                    ),
                    FeedArticle(
                        article_feed_id="article-3",
                        title="Article 3",
                        summary="Summary 3",
                        content="Description 3",
                        authors=["Author"],
                        contributors=["Contributor"],
                        tags=["Some tag"],
                        link="https//example.com/article/3",
                        published_at=datetime.now(tz=UTC),
                        updated_at=datetime.now(tz=UTC),
                    ),
                ],
                feed,
            )

        assert Article.objects.count() == 3
        existing_article.refresh_from_db()
        assert existing_article.title == "Article updated"
        assert list(
            Article.objects.annotate(tag_slugs=ArrayAgg("tags__slug")).values_list(
                "tag_slugs", flat=True
            )
        ) == [[tag1.slug, tag2.slug], [tag1.slug, tag2.slug], [tag1.slug, tag2.slug]]

    def test_update_and_create_articles_empty_list(self, django_assert_num_queries):
        feed = FeedFactory()

        with django_assert_num_queries(0):
            Article.objects.update_or_create_from_articles_list([], feed)

        assert Article.objects.count() == 0

    def test_count_articles_of_reading_lists(self, django_assert_num_queries):
        feed = FeedFactory()
        reading_list1 = ReadingListFactory(user=feed.user)
        reading_list2 = ReadingListFactory(
            user=feed.user, read_status=constants.ReadStatus.ONLY_READ
        )
        reading_list3 = ReadingListFactory(
            user=feed.user, favorite_status=constants.FavoriteStatus.ONLY_FAVORITE
        )
        reading_lists_with_tags = list(
            ReadingList.objects.select_related("user").prefetch_related("tags").all()
        )
        ArticleFactory(feed=feed)
        ArticleFactory(feed=feed, is_read=True)

        with django_assert_num_queries(1):
            counts = Article.objects.count_articles_of_reading_lists(reading_lists_with_tags)

        assert counts == {
            reading_list1.slug: 2,
            reading_list2.slug: 1,
            reading_list3.slug: 0,
        }
