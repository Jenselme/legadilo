from datetime import UTC, datetime
from random import choice
from typing import Any

import pytest
import time_machine
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models

from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag, ReadingList, ReadingListTag
from legadilo.reading.models.article import _build_filters_from_reading_list
from legadilo.reading.tests.factories import (
    ArticleFactory,
    ReadingListFactory,
    TagFactory,
)
from legadilo.reading.utils.article_fetching import ArticleData
from legadilo.utils.time import utcdt, utcnow


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

    assert filters == expected_filter


@pytest.mark.django_db()
class TestArticleQuerySet:
    def test_for_user(self, user, other_user):
        article = ArticleFactory(user=user)
        ArticleFactory(user=other_user)

        articles = Article.objects.get_queryset().for_user(user)

        assert list(articles) == [article]

    def test_only_unread(self, user):
        ArticleFactory(user=user, read_at=utcnow())
        unread_article = ArticleFactory(user=user, read_at=None)

        articles = Article.objects.get_queryset().only_unread()

        assert list(articles) == [unread_article]

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
            articles = Article.objects.get_articles_of_reading_list(reading_list)

        assert list(articles) == [
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

        with django_assert_num_queries(3):
            articles = list(Article.objects.get_articles_of_reading_list(reading_list))

        assert list(articles) == [
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

        with django_assert_num_queries(3):
            articles = list(Article.objects.get_articles_of_reading_list(reading_list))

        assert articles == [
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

        with django_assert_num_queries(3):
            articles = list(Article.objects.get_articles_of_reading_list(reading_list))

        assert articles == [
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

        with django_assert_num_queries(3):
            articles = list(Article.objects.get_articles_of_reading_list(reading_list))

        assert list(articles) == [
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

        with django_assert_num_queries(1):
            articles = Article.objects.get_articles_of_reading_list(reading_list)

        assert list(articles) == [
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

        with django_assert_num_queries(1):
            articles = Article.objects.get_articles_of_reading_list(reading_list)

        assert list(articles) == [
            article_to_include_linked_to_all_tags,
            article_to_include_linked_to_deleted_tag_to_exclude,
        ]

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
    def test_update_articles_from_action(
        self, action: constants.UpdateArticleActions, attrs: dict[str, bool | str]
    ):
        article = ArticleFactory(
            read_at=choice([datetime(2024, 4, 20, 12, 0, tzinfo=UTC), None]),
            is_favorite=choice([True, False]),
            is_for_later=choice([True, False]),
            opened_at=choice([datetime(2024, 4, 20, 12, 0, tzinfo=UTC), None]),
        )

        with time_machine.travel("2024-04-20 12:00:00"):
            Article.objects.get_queryset().filter(id=article.id).update_articles_from_action(action)

        article.refresh_from_db()
        for attr_name, attr_value in attrs.items():
            assert getattr(article, attr_name) == attr_value


@pytest.mark.django_db()
class TestArticleManager:
    def test_update_and_create_articles(self, user, django_assert_num_queries):
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        existing_article_to_update = ArticleFactory(
            title="Old title",
            content="Old content",
            user=user,
            external_article_id="existing-article-feed",
            updated_at=utcdt(2023, 4, 20),
            read_at=utcnow(),
            initial_source_type=constants.ArticleSourceType.FEED,
        )
        existing_article_to_keep = ArticleFactory(
            title="Title to keep",
            content="Content to keep",
            user=user,
            updated_at=utcdt(2024, 4, 20),
        )
        ArticleTag.objects.create(
            article=existing_article_to_keep,
            tag=tag1,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        now_dt = utcnow()

        with django_assert_num_queries(7):
            Article.objects.update_or_create_from_articles_list(
                user,
                [
                    ArticleData(
                        external_article_id="some-article-1",
                        title="Article 1",
                        summary="Summary 1",
                        content="Description 1" + " word " * user.settings.default_reading_time * 3,
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        link="https//example.com/article/1",
                        preview_picture_url="https://example.com/preview.png",
                        preview_picture_alt="Some image alt",
                        published_at=now_dt,
                        updated_at=now_dt,
                        source_title="Some site",
                        language="fr",
                    ),
                    ArticleData(
                        external_article_id=existing_article_to_update.external_article_id,
                        link=existing_article_to_update.link,
                        title="Article updated",
                        summary="Summary updated",
                        content="Description updated",
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        preview_picture_url="",
                        preview_picture_alt="",
                        published_at=now_dt,
                        updated_at=now_dt,
                        source_title="Some site",
                        language="fr",
                    ),
                    ArticleData(
                        external_article_id=existing_article_to_keep.external_article_id,
                        link=existing_article_to_keep.link,
                        title="Updated article",
                        summary="Summary updated",
                        content="Description updated",
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        preview_picture_url="",
                        preview_picture_alt="",
                        published_at=utcdt(2024, 4, 19),
                        updated_at=utcdt(2024, 4, 19),
                        source_title="Some site",
                        language="fr",
                    ),
                    ArticleData(
                        external_article_id="article-3",
                        title="Article 3",
                        summary="Summary 3",
                        content="Description 3",
                        authors=["Author"],
                        contributors=["Contributor"],
                        tags=["Some tag"],
                        link="https//example.com/article/3",
                        preview_picture_url="",
                        preview_picture_alt="",
                        published_at=now_dt,
                        updated_at=now_dt,
                        source_title="Some site",
                        language="fr",
                    ),
                ],
                [tag1, tag2],
                source_type=constants.ArticleSourceType.MANUAL,
            )

        assert Article.objects.count() == 4
        existing_article_to_update.refresh_from_db()
        assert existing_article_to_update.title == "Article updated"
        assert existing_article_to_update.slug == "article-updated"
        assert existing_article_to_update.updated_at == now_dt
        assert existing_article_to_update.read_at is None
        assert existing_article_to_update.initial_source_type == constants.ArticleSourceType.MANUAL
        existing_article_to_keep.refresh_from_db()
        assert existing_article_to_keep.title == "Title to keep"
        assert existing_article_to_keep.slug == "title-to-keep"
        assert existing_article_to_keep.content == "Content to keep"
        assert existing_article_to_keep.updated_at == utcdt(2024, 4, 20)
        other_article = Article.objects.exclude(
            id__in=[existing_article_to_update.id, existing_article_to_keep.id]
        ).first()
        assert other_article is not None
        assert other_article.title == "Article 1"
        assert other_article.slug == "article-1"
        assert other_article.reading_time == 3
        assert list(
            Article.objects.annotate(tag_slugs=ArrayAgg("tags__slug")).values_list(
                "tag_slugs", flat=True
            )
        ) == [
            [tag1.slug, tag2.slug],
            [tag1.slug, tag2.slug],
            [tag1.slug, tag2.slug],
            [tag1.slug, tag2.slug],
        ]

    def test_same_link_multiple_times(self, user, django_assert_num_queries):
        now_dt = utcnow()

        with django_assert_num_queries(4):
            Article.objects.update_or_create_from_articles_list(
                user,
                [
                    ArticleData(
                        external_article_id="some-article-1",
                        title="Article 1",
                        summary="Summary 1",
                        content="Description 1" + " word " * user.settings.default_reading_time * 3,
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        link="https//example.com/article/1",
                        preview_picture_url="https://example.com/preview.png",
                        preview_picture_alt="Some image alt",
                        published_at=now_dt,
                        updated_at=now_dt,
                        source_title="Some site",
                        language="fr",
                    ),
                    ArticleData(
                        external_article_id="some-article-1",
                        link="https//example.com/article/1",
                        title="Article updated",
                        summary="Summary updated",
                        content="Description updated",
                        authors=["Author"],
                        contributors=[],
                        tags=[],
                        preview_picture_url="",
                        preview_picture_alt="",
                        published_at=now_dt,
                        updated_at=now_dt,
                        source_title="Some site",
                        language="fr",
                    ),
                ],
                [],
                source_type=constants.ArticleSourceType.MANUAL,
            )

        assert Article.objects.count() == 1
        other_article = Article.objects.get()
        assert other_article.title == "Article 1"
        assert other_article.slug == "article-1"
        assert other_article.reading_time == 3

    def test_manually_readd_read_article(self, user, django_assert_num_queries):
        now_dt = utcnow()
        existing_article = ArticleFactory(
            title="Old title",
            content="Old content",
            user=user,
            external_article_id="existing-article-feed",
            updated_at=utcdt(2023, 4, 20),
            read_at=now_dt,
        )
        article_data = ArticleData(
            external_article_id=existing_article.external_article_id,
            link=existing_article.link,
            title=existing_article.title,
            summary=existing_article.summary,
            content=existing_article.content,
            authors=existing_article.authors,
            contributors=existing_article.contributors,
            tags=existing_article.external_tags,
            published_at=now_dt,
            updated_at=now_dt,
            source_title="Some site",
            preview_picture_url="https://example.com/preview.png",
            preview_picture_alt="Some image alt",
            language="fr",
        )

        with django_assert_num_queries(4):
            Article.objects.update_or_create_from_articles_list(
                user, [article_data], [], source_type=constants.ArticleSourceType.MANUAL
            )

        existing_article.refresh_from_db()
        assert existing_article.read_at is None

    def test_readd_read_article_from_a_feed(self, user, django_assert_num_queries):
        now_dt = utcnow()
        existing_article = ArticleFactory(
            title="Old title",
            content="Old content",
            user=user,
            external_article_id="existing-article-feed",
            updated_at=utcdt(2023, 4, 20),
            read_at=now_dt,
        )
        article_data = ArticleData(
            external_article_id=existing_article.external_article_id,
            link=existing_article.link,
            title=existing_article.title,
            summary=existing_article.summary,
            content=existing_article.content,
            authors=existing_article.authors,
            contributors=existing_article.contributors,
            tags=existing_article.external_tags,
            published_at=now_dt,
            updated_at=now_dt,
            source_title="Some site",
            preview_picture_url="https://example.com/preview.png",
            preview_picture_alt="Some image alt",
            language="fr",
        )

        with django_assert_num_queries(4):
            Article.objects.update_or_create_from_articles_list(
                user, [article_data], [], source_type=constants.ArticleSourceType.FEED
            )

        existing_article.refresh_from_db()
        assert existing_article.read_at == now_dt

    def test_count_unread_articles_of_reading_lists(self, user, django_assert_num_queries):
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
            counts = Article.objects.count_unread_articles_of_reading_lists(
                user, reading_lists_with_tags
            )

        assert counts == {
            reading_list1.slug: 1,
            reading_list2.slug: 0,
            reading_list3.slug: 0,
        }

    def test_get_articles_of_tag(self, user, django_assert_num_queries):
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
        article_link_to_tag_to_display_and_deleted_tag = ArticleFactory(
            title="Article linked to tag to display and some other deleted tag", user=user
        )
        ArticleTag.objects.create(
            tag=tag_to_display, article=article_link_to_tag_to_display_and_deleted_tag
        )
        ArticleTag.objects.create(
            tag=other_tag,
            article=article_link_to_tag_to_display_and_deleted_tag,
            tagging_reason=constants.TaggingReason.DELETED,
        )

        with django_assert_num_queries(2):
            articles = list(Article.objects.get_articles_of_tag(tag_to_display).order_by("id"))

        assert list(articles) == [
            article_linked_only_to_tag_to_display,
            article_linked_to_all_tags,
            article_link_to_tag_to_display_and_deleted_tag,
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
        ("initial_data", "expected_data", "expected_was_updated"),
        [
            pytest.param(
                {
                    "title": "Initial title",
                    "content": "Initial content",
                    "updated_at": utcdt(2024, 4, 21),
                },
                {
                    "title": "Initial title",
                    "content": "Initial content",
                    "updated_at": utcdt(2024, 4, 21),
                },
                False,
                id="initial-data-more-recent-than-update-proposal",
            ),
            pytest.param(
                {
                    "title": "Initial title",
                    "content": "",
                    "updated_at": utcdt(2024, 4, 21),
                },
                {
                    "title": "Initial title",
                    "content": "Updated content",
                    "updated_at": utcdt(2024, 4, 21),
                },
                True,
                id="initial-data-more-recent-than-update-proposal-but-update-has-content",
            ),
            pytest.param(
                {
                    "title": "Initial title",
                    "summary": "Initial summary",
                    "content": "Initial content",
                    "updated_at": utcdt(2024, 4, 19),
                    "external_tags": ["Initial tag", "Some tag"],
                    "authors": ["Author 1", "Author 2"],
                    "contributors": ["Contributor 1", "Contributor 2"],
                },
                {
                    "title": "Updated title",
                    "summary": "Updated summary",
                    "content": "Updated content",
                    "updated_at": utcdt(2024, 4, 20),
                    "external_tags": ["Initial tag", "Some tag", "Updated tag"],
                    "authors": ["Author 1", "Author 2", "Author 3"],
                    "contributors": ["Contributor 1", "Contributor 2", "Contributor 3"],
                },
                True,
                id="initial-data-less-recent-than-update-proposal",
            ),
        ],
    )
    def test_update_article_from_data(
        self, user, initial_data: dict, expected_data: dict, expected_was_updated: bool
    ):
        article = ArticleFactory.build(**initial_data, user=user)

        was_updated = article.update_article_from_data(
            ArticleData(
                external_article_id="some-article-1",
                title="Updated title",
                summary="Updated summary",
                content="Updated content",
                authors=["Author 2", "Author 3"],
                contributors=["Contributor 2", "Contributor 3"],
                tags=["Some tag", "Updated tag"],
                link="https//example.com/article/1",
                preview_picture_url="https://example.com/preview.png",
                preview_picture_alt="Some image alt",
                published_at=utcdt(2024, 4, 20),
                updated_at=utcdt(2024, 4, 20),
                source_title="Some site",
                language="fr",
            )
        )

        assert was_updated == expected_was_updated
        for attr, value in expected_data.items():
            assert getattr(article, attr) == value

    def test_update_article_from_data_article_data_is_missing_some_data(self, user):
        initial_data = {
            "title": "Initial title",
            "summary": "Initial summary",
            "content": "Initial content",
            "updated_at": utcdt(2024, 4, 19),
            "reading_time": 3,
        }
        expected_data = {
            "title": "Updated title",
            "summary": "Initial summary",
            "content": "Initial content",
            "updated_at": utcdt(2024, 4, 20),
            "reading_time": 3,
        }
        article = ArticleFactory.build(**initial_data, user=user)

        was_updated = article.update_article_from_data(
            ArticleData(
                external_article_id="some-article-1",
                title="Updated title",
                summary="",
                content="",
                authors=["Author"],
                contributors=[],
                tags=[],
                link="https//example.com/article/1",
                preview_picture_url="",
                preview_picture_alt="",
                published_at=utcdt(2024, 4, 20),
                updated_at=utcdt(2024, 4, 20),
                source_title="Some site",
                language="fr",
            )
        )

        assert was_updated
        for attr, value in expected_data.items():
            assert getattr(article, attr) == value

    @pytest.mark.parametrize(
        ("source_type", "is_from_feed"),
        [
            pytest.param(constants.ArticleSourceType.FEED, True, id="feed"),
            pytest.param(constants.ArticleSourceType.MANUAL, False, id="manual"),
        ],
    )
    def test_is_from_feed(self, source_type, is_from_feed):
        article = ArticleFactory.build(initial_source_type=source_type)

        assert article.is_from_feed == is_from_feed
