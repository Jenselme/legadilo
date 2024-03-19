from datetime import UTC, datetime
from typing import Any

import pytest
import time_machine
from django.db import models

from legadilo.feeds import constants
from legadilo.feeds.models import Article
from legadilo.feeds.tests.factories import ArticleFactory, FeedFactory, ReadingListFactory
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
    def test_get_only_unread_articles(
        self, user, reading_list_kwargs: dict[str, Any], expected_filter: models.Q
    ):
        reading_list = ReadingListFactory.build(**reading_list_kwargs, user=user)

        with time_machine.travel("2024-03-19 21:08:00"):
            filters = Article.objects.get_queryset().build_filters_from_reading_list(reading_list)

        assert filters == models.Q(feed__user=user) & expected_filter


@pytest.mark.django_db()
class TestArticleManager:
    def test_update_and_create_articles(self):
        feed = FeedFactory()
        existing_article = ArticleFactory(
            feed=feed, article_feed_id=f"existing-article-feed-{feed.id}"
        )

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
            feed.id,
        )

        assert Article.objects.count() == 3
        existing_article.refresh_from_db()
        assert existing_article.title == "Article updated"

    def test_update_and_create_articles_empty_list(self):
        feed = FeedFactory()

        Article.objects.update_or_create_from_articles_list([], feed.id)

        assert Article.objects.count() == 0
