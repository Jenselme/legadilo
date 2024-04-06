from datetime import UTC, datetime
from random import choice
from typing import Any

import pytest
import time_machine
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models

from legadilo.feeds import constants
from legadilo.feeds.models import Article, ArticleTag, ReadingList, ReadingListTag
from legadilo.feeds.models.article import _build_filters_from_reading_list
from legadilo.feeds.tests.factories import (
    ArticleFactory,
    FeedFactory,
    ReadingListFactory,
    TagFactory,
)
from legadilo.feeds.utils.feed_parsing import FeedArticle


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
    user, reading_list_kwargs: dict[str, Any], expected_filter: models.Q
):
    reading_list = ReadingListFactory(**reading_list_kwargs, user=user)

    with time_machine.travel("2024-03-19 21:08:00"):
        filters = _build_filters_from_reading_list(reading_list)

    assert filters == models.Q(feed__user=user) & expected_filter


class TestArticleQuerySet:
    def test_for_reading_list_with_tags_basic_include(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(user=user)
        feed = FeedFactory(user=user)
        tag_to_include = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag_to_include,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        article_to_include_linked_many_tags = ArticleFactory(
            title="Article to include linked many tags", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_include_linked_many_tags,
            tag=tag_to_include,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_to_include_linked_many_tags,
            tag=other_tag,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_to_include_one_tag = ArticleFactory(
            title="Article to include linked to one tag", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_include_one_tag,
            tag=tag_to_include,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_would_be_included_if_tag_not_deleted = ArticleFactory(
            title="Article to include if tag not deleted", feed=feed
        )
        ArticleTag.objects.create(
            article=article_would_be_included_if_tag_not_deleted,
            tag=tag_to_include,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        article_linked_only_to_other_tag = ArticleFactory(
            title="Article linked to other tag", feed=feed
        )
        ArticleTag.objects.create(
            article=article_linked_only_to_other_tag,
            tag=other_tag,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )

        with django_assert_num_queries(1):
            articles_paginator = Article.objects.get_articles_of_reading_list(reading_list)

        assert articles_paginator.num_pages == 1
        articles_page = articles_paginator.page(1)
        assert list(articles_page.object_list) == [
            article_to_include_linked_many_tags,
            article_to_include_one_tag,
        ]

    def test_for_reading_list_include_all_tags(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(
            user=user, include_tag_operator=constants.ReadingListTagOperator.ALL
        )
        feed = FeedFactory(user=user)
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag1,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag2,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        article_linked_to_all_tags = ArticleFactory(feed=feed)
        ArticleTag.objects.create(
            article=article_linked_to_all_tags,
            tag=tag1,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_linked_to_all_tags,
            tag=tag2,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_linked_to_one_tag = ArticleFactory(feed=feed)
        ArticleTag.objects.create(
            article=article_linked_to_one_tag,
            tag=tag1,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )

        with django_assert_num_queries(1):
            articles_paginator = Article.objects.get_articles_of_reading_list(reading_list)

        assert articles_paginator.num_pages == 1
        assert articles_paginator.count == 1
        articles_page = articles_paginator.page(1)
        assert list(articles_page.object_list) == [
            article_linked_to_all_tags,
        ]

    def test_for_reading_list_include_any_tags(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(
            user=user, include_tag_operator=constants.ReadingListTagOperator.ANY
        )
        feed = FeedFactory(user=user)
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag1,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag2,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        article_linked_to_all_tags = ArticleFactory(feed=feed)
        ArticleTag.objects.create(
            article=article_linked_to_all_tags,
            tag=tag1,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_linked_to_all_tags,
            tag=tag2,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_to_include_one_tag = ArticleFactory(feed=feed)
        ArticleTag.objects.create(
            article=article_to_include_one_tag,
            tag=tag1,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )

        with django_assert_num_queries(1):
            articles_paginator = Article.objects.get_articles_of_reading_list(reading_list)

        assert articles_paginator.num_pages == 1
        assert articles_paginator.count == 2
        articles_page = articles_paginator.page(1)
        assert list(articles_page.object_list) == [
            article_linked_to_all_tags,
            article_to_include_one_tag,
        ]

    def test_for_reading_list_with_tags_basic_exclude(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(user=user)
        feed = FeedFactory(user=user)
        tag_to_exclude = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag_to_exclude,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        article_to_exclude_linked_many_tags = ArticleFactory(
            title="Article to exclude linked to many tags", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_exclude_linked_many_tags,
            tag=tag_to_exclude,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_to_exclude_linked_many_tags,
            tag=other_tag,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_to_exclude_one_tag = ArticleFactory(
            title="Article to exclude linked to one tag", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_exclude_one_tag,
            tag=tag_to_exclude,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_linked_only_to_other_tag = ArticleFactory(
            title="Article linked to only one other tag", feed=feed
        )
        ArticleTag.objects.create(
            article=article_linked_only_to_other_tag,
            tag=other_tag,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_would_be_excluded_if_tag_not_deleted = ArticleFactory(
            title="Article would be excluded if tag not deleted", feed=feed
        )
        ArticleTag.objects.create(
            article=article_would_be_excluded_if_tag_not_deleted,
            tag=tag_to_exclude,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        article_linked_to_no_tag = ArticleFactory(title="Article linked to no tag", feed=feed)

        with django_assert_num_queries(2):
            articles_paginator = Article.objects.get_articles_of_reading_list(reading_list)
            articles_page = articles_paginator.page(1)

        assert articles_paginator.num_pages == 1
        assert list(articles_page.object_list) == [
            article_linked_only_to_other_tag,
            article_would_be_excluded_if_tag_not_deleted,
            article_linked_to_no_tag,
        ]

    def test_for_reading_list_exclude_any_tags(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(
            user=user, exclude_tag_operator=constants.ReadingListTagOperator.ANY
        )
        feed = FeedFactory(user=user)
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag1,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag2,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        article_to_exclude_linked_many_tags = ArticleFactory(
            title="Article to exclude linked to many tags", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_exclude_linked_many_tags,
            tag=tag1,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_to_exclude_linked_many_tags,
            tag=tag2,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_to_exclude_one_tag = ArticleFactory(
            title="Article to exclude linked to one tag", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_exclude_one_tag,
            tag=tag1,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_would_be_excluded_if_tag_not_deleted = ArticleFactory(
            title="Article would be excluded if tag not deleted", feed=feed
        )
        ArticleTag.objects.create(
            article=article_would_be_excluded_if_tag_not_deleted,
            tag=tag1,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        ArticleTag.objects.create(
            article=article_would_be_excluded_if_tag_not_deleted,
            tag=other_tag,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_linked_to_no_tag = ArticleFactory(title="Article linked to no tag", feed=feed)

        with django_assert_num_queries(2):
            articles_paginator = Article.objects.get_articles_of_reading_list(reading_list)
            articles_page = articles_paginator.page(1)

        assert articles_paginator.num_pages == 1
        assert list(articles_page.object_list) == [
            article_would_be_excluded_if_tag_not_deleted,
            article_linked_to_no_tag,
        ]

    def test_for_reading_list_exclude_all_tags(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(
            user=user, exclude_tag_operator=constants.ReadingListTagOperator.ALL
        )
        feed = FeedFactory(user=user)
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag1,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag2,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        article_to_exclude_linked_to_all_tags = ArticleFactory(
            title="Article to exclude linked to many tags", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_exclude_linked_to_all_tags,
            tag=tag1,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_to_exclude_linked_to_all_tags,
            tag=tag2,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_linked_to_one_tag = ArticleFactory(
            title="Article to exclude linked to one tag", feed=feed
        )
        ArticleTag.objects.create(
            article=article_linked_to_one_tag,
            tag=tag1,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_would_be_excluded_if_tag_not_deleted = ArticleFactory(
            title="Article would be excluded if tag not deleted", feed=feed
        )
        ArticleTag.objects.create(
            article=article_would_be_excluded_if_tag_not_deleted,
            tag=tag1,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        ArticleTag.objects.create(
            article=article_would_be_excluded_if_tag_not_deleted,
            tag=tag2,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_linked_to_no_tag = ArticleFactory(title="Article linked to no tag", feed=feed)

        with django_assert_num_queries(2):
            articles_paginator = Article.objects.get_articles_of_reading_list(reading_list)
            articles_page = articles_paginator.page(1)

        assert articles_paginator.num_pages == 1
        assert list(articles_page.object_list) == [
            article_linked_to_one_tag,
            article_would_be_excluded_if_tag_not_deleted,
            article_linked_to_no_tag,
        ]

    def test_for_reading_list_with_tags(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(
            user=user,
            include_tag_operator=constants.ReadingListTagOperator.ALL,
            exclude_tag_operator=constants.ReadingListTagOperator.ANY,
        )
        feed = FeedFactory(user=user)
        tag1_to_include = TagFactory(user=user)
        tag2_to_include = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        tag1_to_exclude = TagFactory(user=user)
        tag2_to_exclude = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag1_to_include,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag2_to_include,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag1_to_exclude,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag2_to_exclude,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        article_to_include_linked_to_all_tags = ArticleFactory(
            title="Article cannot be included", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_include_linked_to_all_tags,
            tag=tag1_to_include,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_to_include_linked_to_all_tags,
            tag=tag2_to_include,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_to_include_linked_to_all_tags,
            tag=other_tag,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_cannot_be_included_linked_to_tag_to_exclude = ArticleFactory(
            title="Article cannot be included linked to tag to exclude", feed=feed
        )
        ArticleTag.objects.create(
            article=article_cannot_be_included_linked_to_tag_to_exclude,
            tag=tag1_to_include,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_cannot_be_included_linked_to_tag_to_exclude,
            tag=tag2_to_include,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_cannot_be_included_linked_to_tag_to_exclude,
            tag=tag1_to_exclude,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_cannot_be_included_linked_to_one_tag = ArticleFactory(
            title="Article to include one tag", feed=feed
        )
        ArticleTag.objects.create(
            article=article_cannot_be_included_linked_to_one_tag,
            tag=tag1_to_include,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_cannot_be_included_linked_to_deleted_tag_to_include = ArticleFactory(
            title="Article to include linked many tags", feed=feed
        )
        ArticleTag.objects.create(
            article=article_cannot_be_included_linked_to_deleted_tag_to_include,
            tag=tag1_to_include,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        ArticleTag.objects.create(
            article=article_cannot_be_included_linked_to_deleted_tag_to_include,
            tag=tag2_to_include,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        article_to_include_linked_to_deleted_tag_to_exclude = ArticleFactory(
            title="Article to include linked to deleted tag to exclude", feed=feed
        )
        ArticleTag.objects.create(
            article=article_to_include_linked_to_deleted_tag_to_exclude,
            tag=tag1_to_include,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_to_include_linked_to_deleted_tag_to_exclude,
            tag=tag2_to_include,
            tagging_reason=constants.TaggingReason.FROM_FEED,
        )
        ArticleTag.objects.create(
            article=article_to_include_linked_to_deleted_tag_to_exclude,
            tag=tag1_to_exclude,
            tagging_reason=constants.TaggingReason.DELETED,
        )

        with django_assert_num_queries(2):
            articles_paginator = Article.objects.get_articles_of_reading_list(reading_list)
            articles_page = articles_paginator.page(1)

        assert articles_paginator.num_pages == 1
        assert list(articles_page.object_list) == [
            article_to_include_linked_to_all_tags,
            article_to_include_linked_to_deleted_tag_to_exclude,
        ]


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
            ReadingList.objects.select_related("user").prefetch_related("reading_list_tags").all()
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

    def test_get_articles_of_tag(self):
        feed = FeedFactory()
        tag_to_display = TagFactory(user=feed.user)
        other_tag = TagFactory(user=feed.user)
        article_linked_only_to_tag_to_display = ArticleFactory(
            title="Article linked only to tag to display", feed=feed
        )
        ArticleTag.objects.create(tag=tag_to_display, article=article_linked_only_to_tag_to_display)
        article_linked_to_all_tags = ArticleFactory(title="Article linked to all tags", feed=feed)
        ArticleTag.objects.create(tag=tag_to_display, article=article_linked_to_all_tags)
        ArticleTag.objects.create(tag=other_tag, article=article_linked_to_all_tags)
        article_linked_to_deleted_tag_to_display = ArticleFactory(
            title="Article linked to deleted tag to display", feed=feed
        )
        ArticleTag.objects.create(
            tag=tag_to_display,
            article=article_linked_to_deleted_tag_to_display,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        article_linked_to_other_tag = ArticleFactory(title="Article linked to other tag", feed=feed)
        ArticleTag.objects.create(tag=other_tag, article=article_linked_to_other_tag)

        articles_paginator = Article.objects.get_articles_of_tag(tag_to_display)

        assert articles_paginator.num_pages == 1
        page = articles_paginator.page(1)
        assert list(page.object_list) == [
            article_linked_only_to_tag_to_display,
            article_linked_to_all_tags,
        ]


class TestArticleModel:
    @pytest.mark.parametrize(
        ("action", "attr", "value"),
        [
            pytest.param(
                constants.UpdateArticleActions.MARK_AS_READ, "is_read", True, id="mark-as-read"
            ),
            pytest.param(
                constants.UpdateArticleActions.MARK_AS_UNREAD, "is_read", False, id="mark-as-unread"
            ),
            pytest.param(
                constants.UpdateArticleActions.MARK_AS_FAVORITE,
                "is_favorite",
                True,
                id="mark-as-favorite",
            ),
            pytest.param(
                constants.UpdateArticleActions.UNMARK_AS_FAVORITE,
                "is_favorite",
                False,
                id="unmark-as-favorite",
            ),
        ],
    )
    def test_update_article(self, action: constants.UpdateArticleActions, attr: str, value: bool):
        article = ArticleFactory.build(
            is_read=choice([True, False]), is_favorite=choice([True, False])
        )

        article.update_article(action)

        assert getattr(article, attr) is value
