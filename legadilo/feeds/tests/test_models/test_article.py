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
    ReadingListFactory,
    TagFactory,
)
from legadilo.feeds.utils.feed_parsing import ArticleData
from legadilo.utils.time import utcnow


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
            {"for_later_status": constants.ForLaterStatus.ONLY_FOR_LATER},
            models.Q(is_for_later=True),
            id="for_later_only",
        ),
        pytest.param(
            {"for_later_status": constants.ForLaterStatus.ONLY_NOT_FOR_LATER},
            models.Q(is_for_later=False),
            id="not_for_later_only",
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
                "articles_reading_time": 5,
                "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.MORE_THAN,
            },
            models.Q(reading_time__gte=5),
            id="more-than-5-minutes-reading-time",
        ),
        pytest.param(
            {
                "articles_reading_time": 5,
                "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN,
            },
            models.Q(reading_time__lte=5),
            id="less-than-5-minutes-reading-time",
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
                "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.MORE_THAN,
                "articles_reading_time": 5,
            },
            models.Q(is_read=False)
            & models.Q(is_favorite=True)
            & models.Q(
                published_at__gt=datetime(2024, 2, 19, 21, 8, 0, tzinfo=UTC),
            )
            & models.Q(reading_time__gte=5),
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

    assert filters == models.Q(user=user) & expected_filter


class TestArticleQuerySet:
    def test_for_reading_list_with_tags_basic_include(self, user, django_assert_num_queries):
        reading_list = ReadingListFactory(user=user)
        tag_to_include = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag_to_include,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        article_to_include_linked_many_tags = ArticleFactory(
            title="Article to include linked many tags", user=user
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
            title="Article to include linked to one tag", user=user
        )
        ArticleTag.objects.create(
            article=article_to_include_one_tag,
            tag=tag_to_include,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_would_be_included_if_tag_not_deleted = ArticleFactory(
            title="Article to include if tag not deleted", user=user
        )
        ArticleTag.objects.create(
            article=article_would_be_included_if_tag_not_deleted,
            tag=tag_to_include,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        article_linked_only_to_other_tag = ArticleFactory(
            title="Article linked to other tag", user=user
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
        article_linked_to_all_tags = ArticleFactory(user=user)
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
        article_linked_to_one_tag = ArticleFactory(user=user)
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
        article_linked_to_all_tags = ArticleFactory(user=user)
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
        article_to_include_one_tag = ArticleFactory(user=user)
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
        tag_to_exclude = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag_to_exclude,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        article_to_exclude_linked_many_tags = ArticleFactory(
            title="Article to exclude linked to many tags", user=user
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
            title="Article to exclude linked to one tag", user=user
        )
        ArticleTag.objects.create(
            article=article_to_exclude_one_tag,
            tag=tag_to_exclude,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_linked_only_to_other_tag = ArticleFactory(
            title="Article linked to only one other tag", user=user
        )
        ArticleTag.objects.create(
            article=article_linked_only_to_other_tag,
            tag=other_tag,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_would_be_excluded_if_tag_not_deleted = ArticleFactory(
            title="Article would be excluded if tag not deleted", user=user
        )
        ArticleTag.objects.create(
            article=article_would_be_excluded_if_tag_not_deleted,
            tag=tag_to_exclude,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        article_linked_to_no_tag = ArticleFactory(title="Article linked to no tag", user=user)

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
            title="Article to exclude linked to many tags", user=user
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
            title="Article to exclude linked to one tag", user=user
        )
        ArticleTag.objects.create(
            article=article_to_exclude_one_tag,
            tag=tag1,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_would_be_excluded_if_tag_not_deleted = ArticleFactory(
            title="Article would be excluded if tag not deleted", user=user
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
        article_linked_to_no_tag = ArticleFactory(title="Article linked to no tag", user=user)

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
            title="Article to exclude linked to many tags", user=user
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
            title="Article to exclude linked to one tag", user=user
        )
        ArticleTag.objects.create(
            article=article_linked_to_one_tag,
            tag=tag1,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_would_be_excluded_if_tag_not_deleted = ArticleFactory(
            title="Article would be excluded if tag not deleted", user=user
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
        article_linked_to_no_tag = ArticleFactory(title="Article linked to no tag", user=user)

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
            title="Article cannot be included", user=user
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
            title="Article cannot be included linked to tag to exclude", user=user
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
            title="Article to include one tag", user=user
        )
        ArticleTag.objects.create(
            article=article_cannot_be_included_linked_to_one_tag,
            tag=tag1_to_include,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_cannot_be_included_linked_to_deleted_tag_to_include = ArticleFactory(
            title="Article to include linked many tags", user=user
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
            title="Article to include linked to deleted tag to exclude", user=user
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
    def test_update_and_create_articles(self, user, django_assert_num_queries):
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        existing_article = ArticleFactory(user=user, external_article_id="existing-article-feed")

        with django_assert_num_queries(2):
            Article.objects.update_or_create_from_articles_list(
                user,
                [
                    ArticleData(
                        external_article_id="some-article-1",
                        title="Article 1",
                        summary="Summary 1",
                        content="Description 1",
                        nb_words=650,
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        link="https//example.com/article/1",
                        published_at=datetime.now(tz=UTC),
                        updated_at=datetime.now(tz=UTC),
                    ),
                    ArticleData(
                        external_article_id=existing_article.external_article_id,
                        link=existing_article.link,
                        title="Article updated",
                        summary="Summary updated",
                        content="Description updated",
                        nb_words=2,
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        published_at=datetime.now(tz=UTC),
                        updated_at=datetime.now(tz=UTC),
                    ),
                    ArticleData(
                        external_article_id="article-3",
                        title="Article 3",
                        summary="Summary 3",
                        content="Description 3",
                        nb_words=1,
                        authors=["Author"],
                        contributors=["Contributor"],
                        tags=["Some tag"],
                        link="https//example.com/article/3",
                        published_at=datetime.now(tz=UTC),
                        updated_at=datetime.now(tz=UTC),
                    ),
                ],
                [tag1, tag2],
                source_type=constants.ArticleSourceType.MANUAL,
                source_title="Not a feed",
            )

        assert Article.objects.count() == 3
        existing_article.refresh_from_db()
        assert existing_article.title == "Article updated"
        assert existing_article.slug == "article-updated"
        other_article = Article.objects.exclude(id=existing_article.id).first()
        assert other_article is not None
        assert other_article.title == "Article 1"
        assert other_article.slug == "article-1"
        assert other_article.reading_time == 3
        assert list(
            Article.objects.annotate(tag_slugs=ArrayAgg("tags__slug")).values_list(
                "tag_slugs", flat=True
            )
        ) == [[tag1.slug, tag2.slug], [tag1.slug, tag2.slug], [tag1.slug, tag2.slug]]

    def test_update_and_create_articles_empty_list(self, user, django_assert_num_queries):
        with django_assert_num_queries(0):
            Article.objects.update_or_create_from_articles_list(
                user,
                [],
                [],
                source_type=constants.ArticleSourceType.MANUAL,
                source_title="Not a feed",
            )

        assert Article.objects.count() == 0

    def test_count_articles_of_reading_lists(self, user, django_assert_num_queries):
        reading_list1 = ReadingListFactory(user=user)
        reading_list2 = ReadingListFactory(user=user, read_status=constants.ReadStatus.ONLY_READ)
        reading_list3 = ReadingListFactory(
            user=user, favorite_status=constants.FavoriteStatus.ONLY_FAVORITE
        )
        reading_lists_with_tags = list(
            ReadingList.objects.select_related("user").prefetch_related("reading_list_tags").all()
        )
        ArticleFactory(user=user)
        ArticleFactory(user=user, read_at=utcnow())

        with django_assert_num_queries(1):
            counts = Article.objects.count_articles_of_reading_lists(reading_lists_with_tags)

        assert counts == {
            reading_list1.slug: 2,
            reading_list2.slug: 1,
            reading_list3.slug: 0,
        }

    def test_get_articles_of_tag(self, user):
        tag_to_display = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        article_linked_only_to_tag_to_display = ArticleFactory(
            title="Article linked only to tag to display", user=user
        )
        ArticleTag.objects.create(tag=tag_to_display, article=article_linked_only_to_tag_to_display)
        article_linked_to_all_tags = ArticleFactory(title="Article linked to all tags", user=user)
        ArticleTag.objects.create(tag=tag_to_display, article=article_linked_to_all_tags)
        ArticleTag.objects.create(tag=other_tag, article=article_linked_to_all_tags)
        article_linked_to_deleted_tag_to_display = ArticleFactory(
            title="Article linked to deleted tag to display", user=user
        )
        ArticleTag.objects.create(
            tag=tag_to_display,
            article=article_linked_to_deleted_tag_to_display,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        article_linked_to_other_tag = ArticleFactory(title="Article linked to other tag", user=user)
        ArticleTag.objects.create(tag=other_tag, article=article_linked_to_other_tag)

        articles_paginator = Article.objects.get_articles_of_tag(tag_to_display)

        assert articles_paginator.num_pages == 1
        page = articles_paginator.page(1)
        assert list(page.object_list) == [
            article_linked_only_to_tag_to_display,
            article_linked_to_all_tags,
        ]


class TestArticleModel:
    @pytest.mark.django_db()
    def test_generated_fields(self):
        article = ArticleFactory(opened_at=None, read_at=None)
        assert not article.is_read
        assert not article.was_opened

        article = ArticleFactory(opened_at=utcnow(), read_at=utcnow())
        assert article.is_read
        assert article.was_opened

    @pytest.mark.parametrize(
        ("action", "attrs"),
        [
            pytest.param(
                constants.UpdateArticleActions.MARK_AS_READ,
                {"read_at": datetime(2024, 4, 20, 12, 0, tzinfo=UTC), "is_read": True},
                id="mark-as-read",
            ),
            pytest.param(
                constants.UpdateArticleActions.MARK_AS_UNREAD,
                {"read_at": None, "is_read": False},
                id="mark-as-unread",
            ),
            pytest.param(
                constants.UpdateArticleActions.MARK_AS_FAVORITE,
                {"is_favorite": True},
                id="mark-as-favorite",
            ),
            pytest.param(
                constants.UpdateArticleActions.UNMARK_AS_FAVORITE,
                {"is_favorite": False},
                id="unmark-as-favorite",
            ),
            pytest.param(
                constants.UpdateArticleActions.MARK_AS_FOR_LATER,
                {"is_for_later": True},
                id="mark-as-for-later",
            ),
            pytest.param(
                constants.UpdateArticleActions.UNMARK_AS_FOR_LATER,
                {"is_for_later": False},
                id="unmark-as-for-later",
            ),
            pytest.param(
                constants.UpdateArticleActions.MARK_AS_OPENED,
                {"opened_at": datetime(2024, 4, 20, 12, 0, tzinfo=UTC), "was_opened": True},
                id="mark-as-opened",
            ),
        ],
    )
    def test_update_article(
        self, action: constants.UpdateArticleActions, attrs: dict[str, bool | str]
    ):
        article = ArticleFactory.build(
            read_at=choice([datetime(2024, 4, 20, 12, 0, tzinfo=UTC), None]),
            is_favorite=choice([True, False]),
            is_for_later=choice([True, False]),
            opened_at=choice([datetime(2024, 4, 20, 12, 0, tzinfo=UTC), None]),
        )

        with time_machine.travel("2024-04-20 12:00:00"):
            article.update_article(action)

        for attr_name, attr_value in attrs.items():
            assert getattr(article, attr_name) == attr_value
