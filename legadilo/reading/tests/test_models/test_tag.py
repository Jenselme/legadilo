# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from legadilo.reading import constants
from legadilo.reading.models import ArticleTag, ReadingListTag, Tag
from legadilo.reading.models.tag import SubTagMapping
from legadilo.reading.tests.factories import ArticleFactory, ReadingListFactory, TagFactory


@pytest.mark.django_db
class TestSubTagMappingManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag1 = TagFactory(title="Tag 1", user=user)
        self.sub_tag1 = TagFactory(title="Sub tag 1", user=user)
        SubTagMapping.objects.create(base_tag=self.tag1, sub_tag=self.sub_tag1)
        self.tag2 = TagFactory(title="Tag 2", user=user)
        self.sub_tag2 = TagFactory(title="Sub tag 2", user=user)
        SubTagMapping.objects.create(base_tag=self.tag2, sub_tag=self.sub_tag2)

    def test_get_selected_mappings(self):
        choices = SubTagMapping.objects.get_selected_mappings(self.tag1)

        assert choices == [self.sub_tag1.slug]

    def test_associate_tag_with_sub_tags(self, user, django_assert_num_queries):
        new_tag = TagFactory(title="New tag", user=user)

        with django_assert_num_queries(6):
            SubTagMapping.objects.associate_tag_with_sub_tags(self.tag1, [new_tag.slug])

        assert set(self.tag1.sub_tags.all().values_list("slug", flat=True)) == {
            new_tag.slug,
            self.sub_tag1.slug,
        }

    def test_associate_tag_with_sub_tags_clear_existing(self, user, django_assert_num_queries):
        new_tag = TagFactory(title="New tag", user=user)

        with django_assert_num_queries(7):
            SubTagMapping.objects.associate_tag_with_sub_tags(
                self.tag1, [new_tag.slug], clear_existing=True
            )

        assert set(self.tag1.sub_tags.all().values_list("slug", flat=True)) == {
            new_tag.slug,
        }


@pytest.mark.django_db
class TestTagManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag1 = TagFactory(user=user, title="Super tag for search")
        self.tag2 = TagFactory(user=user)
        self.existing_tag_with_spaces = TagFactory(
            user=user, title="Existing tag with spaces", slug="existing-tag-with-spaces"
        )
        self.other_user_tag = TagFactory()

    def test_get_all_choices(self, user):
        choices = list(Tag.objects.get_all_choices(user))

        assert choices == [
            (self.existing_tag_with_spaces.slug, self.existing_tag_with_spaces.title),
            (self.tag1.slug, self.tag1.title),
            (self.tag2.slug, self.tag2.title),
        ]

    def test_all_choices_with_hierarchy(self, user, other_user, django_assert_num_queries):
        self.tag1.sub_tags.add(self.tag2)
        tag3 = TagFactory(user=user)
        tag4 = TagFactory(user=user)
        self.tag2.sub_tags.add(tag3, tag4)

        with django_assert_num_queries(2):
            choices, hierarchy = Tag.objects.get_all_choices_with_hierarchy(user)

        assert choices == [
            (self.existing_tag_with_spaces.slug, self.existing_tag_with_spaces.title),
            (self.tag1.slug, self.tag1.title),
            (self.tag2.slug, self.tag2.title),
            (tag3.slug, tag3.title),
            (tag4.slug, tag4.title),
        ]
        assert hierarchy == {
            self.existing_tag_with_spaces.slug: [],
            self.tag1.slug: [{"title": self.tag2.title, "slug": self.tag2.slug}],
            self.tag2.slug: [
                {"title": tag3.title, "slug": tag3.slug},
                {"title": tag4.title, "slug": tag4.slug},
            ],
            tag3.slug: [],
            tag4.slug: [],
        }

    def test_get_or_create_from_list(self, django_assert_num_queries, user):
        with django_assert_num_queries(4):
            tags = Tag.objects.get_or_create_from_list(
                user,
                [self.tag1.slug, self.other_user_tag.slug, "New tag", "Existing tag with spaces"],
            )

        assert len(tags) == 4
        assert Tag.objects.count() == 6
        assert tags[0] == self.existing_tag_with_spaces
        assert tags[1] == self.tag1
        assert tags[2].title == self.other_user_tag.slug
        assert tags[2].slug == self.other_user_tag.slug
        assert tags[2].user == user
        assert tags[3].title == "New tag"
        assert tags[3].slug == "new-tag"
        assert tags[3].user == user

    def test_get_or_create_from_list_no_new(self, django_assert_num_queries, user):
        with django_assert_num_queries(3):
            tags = Tag.objects.get_or_create_from_list(user, [self.tag1.slug])

        assert len(tags) == 1
        assert Tag.objects.count() == 4
        assert tags[0] == self.tag1

    def test_get_slugs_to_ids(self, user, other_user):
        tag = TagFactory(user=user, slug="some-slug")
        TagFactory(user=user)
        TagFactory(user=other_user, slug=tag.slug)

        slugs_to_ids = Tag.objects.get_slugs_to_ids(user, [tag.slug])

        assert slugs_to_ids == {tag.slug: tag.id}

    def test_list_for_admin(self, user):
        TagFactory(title="Tag other user")
        article = ArticleFactory(user=user)
        ArticleTag.objects.create(article=article, tag=self.tag1)

        all_tags = Tag.objects.list_for_admin(user)

        assert all_tags == [
            self.existing_tag_with_spaces,
            self.tag1,
            self.tag2,
        ]
        assert all_tags[0].annot_articles_count == 0  # type: ignore[attr-defined]
        assert all_tags[1].annot_articles_count == 1  # type: ignore[attr-defined]
        assert all_tags[2].annot_articles_count == 0  # type: ignore[attr-defined]

    def test_list_for_admin_with_search(self, user):
        all_tags = Tag.objects.list_for_admin(user, searched_text="seArcH")

        assert all_tags == [
            self.tag1,
        ]


@pytest.mark.django_db
class TestArticleTagQuerySet:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user, other_user):
        self.article = ArticleFactory(user=user)
        self.tag1 = TagFactory(user=user)
        self.tag2 = TagFactory(user=user)
        self.tag3 = TagFactory(user=user)
        self.article_tag1 = ArticleTag.objects.create(
            tag=self.tag1, article=self.article, tagging_reason=constants.TaggingReason.FROM_FEED
        )
        self.article_tag2 = ArticleTag.objects.create(
            tag=self.tag2, article=self.article, tagging_reason=constants.TaggingReason.DELETED
        )
        self.article_tag3 = ArticleTag.objects.create(
            tag=self.tag3,
            article=self.article,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )

    def test_for_reading_list(self):
        article_tags = ArticleTag.objects.get_queryset().for_reading_list().order_by("id")

        assert list(article_tags) == [self.article_tag1, self.article_tag3]

    def test_for_articles_and_tags(self):
        article_tags = list(
            ArticleTag.objects.get_queryset().for_articles_and_tags(
                [self.article], [self.tag1, self.tag2]
            )
        )

        assert article_tags == [self.article_tag1, self.article_tag2]

    def test_for_deleted_urls(self):
        article_tags_marked_as_deleted = list(
            ArticleTag.objects.get_queryset().for_deleted_urls([
                (self.article.id, self.tag1.id),
                (self.article.id, self.tag2.id),
                (self.article.id, self.tag3.id),
            ])
        )

        assert article_tags_marked_as_deleted == [self.article_tag2]


@pytest.mark.django_db
class TestArticleTagManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article1 = ArticleFactory(user=user)
        self.article2 = ArticleFactory(user=user)
        self.tag1 = TagFactory(user=user)
        self.tag2 = TagFactory(user=user)
        self.tag3 = TagFactory(user=user)
        # The article already has the tag, nothing must happen.
        ArticleTag.objects.create(
            article=self.article1, tag=self.tag1, tagging_reason=constants.TaggingReason.FROM_FEED
        )
        # The user deleted the tag, nothing must happen.
        ArticleTag.objects.create(
            article=self.article1, tag=self.tag2, tagging_reason=constants.TaggingReason.DELETED
        )
        # The user added a tag manually, nothing must happen.
        ArticleTag.objects.create(
            article=self.article1,
            tag=self.tag3,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )

    def test_get_selected_values(self):
        choices = list(ArticleTag.objects.get_selected_values())

        assert choices == [self.tag1.slug, self.tag3.slug]

    def test_associate_articles_with_tags(self, user, django_assert_num_queries):
        articles = [self.article1, self.article2]
        tags = [self.tag1, self.tag2]

        with django_assert_num_queries(2):
            ArticleTag.objects.associate_articles_with_tags(
                articles, tags, tagging_reason=constants.TaggingReason.FROM_FEED
            )

        created_article_tags = list(ArticleTag.objects.values("article", "tag", "tagging_reason"))
        assert created_article_tags == [
            {
                "article": self.article1.id,
                "tag": self.tag1.id,
                "tagging_reason": constants.TaggingReason.FROM_FEED,
            },
            {
                "article": self.article1.id,
                "tag": self.tag2.id,
                "tagging_reason": constants.TaggingReason.DELETED,
            },
            {
                "article": self.article1.id,
                "tag": self.tag3.id,
                "tagging_reason": constants.TaggingReason.ADDED_MANUALLY,
            },
            {
                "article": self.article2.id,
                "tag": self.tag1.id,
                "tagging_reason": constants.TaggingReason.FROM_FEED,
            },
            {
                "article": self.article2.id,
                "tag": self.tag2.id,
                "tagging_reason": constants.TaggingReason.FROM_FEED,
            },
        ]

    def test_associate_articles_with_tags_readd_deleted(self, user, django_assert_num_queries):
        articles = [self.article1]
        tags = [self.tag1, self.tag2]

        with django_assert_num_queries(2):
            ArticleTag.objects.associate_articles_with_tags(
                articles, tags, tagging_reason=constants.TaggingReason.FROM_FEED, readd_deleted=True
            )

        created_article_tags = list(ArticleTag.objects.values("article", "tag", "tagging_reason"))
        assert created_article_tags == [
            {
                "article": self.article1.id,
                "tag": self.tag1.id,
                "tagging_reason": constants.TaggingReason.FROM_FEED,
            },
            {
                "article": self.article1.id,
                "tag": self.tag2.id,
                "tagging_reason": constants.TaggingReason.ADDED_MANUALLY,
            },
            {
                "article": self.article1.id,
                "tag": self.tag3.id,
                "tagging_reason": constants.TaggingReason.ADDED_MANUALLY,
            },
        ]

    def test_dissociate_articles_with_tags(self, user, django_assert_num_queries):
        with django_assert_num_queries(1):
            ArticleTag.objects.dissociate_articles_with_tags(
                [self.article1, self.article2], [self.tag1, self.tag2]
            )

        assert list(ArticleTag.objects.values("article", "tag", "tagging_reason")) == [
            {"article": self.article1.id, "tag": self.tag1.id, "tagging_reason": "DELETED"},
            {"article": self.article1.id, "tag": self.tag2.id, "tagging_reason": "DELETED"},
            {"article": self.article1.id, "tag": self.tag3.id, "tagging_reason": "ADDED_MANUALLY"},
        ]

    def test_dissociate_article_with_tags_not_in_list(self, user, django_assert_num_queries):
        with django_assert_num_queries(2):
            ArticleTag.objects.dissociate_article_with_tags_not_in_list(self.article1, [self.tag1])

        assert list(self.article1.article_tags.values_list("tag__slug", "tagging_reason")) == [
            (self.tag1.slug, constants.TaggingReason.FROM_FEED),
            (self.tag2.slug, constants.TaggingReason.DELETED),
            (self.tag3.slug, constants.TaggingReason.DELETED),
        ]


@pytest.mark.django_db
class TestReadingListTagManager:
    def test_get_selected_values(self, user):
        reading_list = ReadingListFactory(user=user)
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
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )

        included_tags = reading_list.reading_list_tags.get_selected_values(
            constants.ReadingListTagFilterType.INCLUDE
        )
        excluded_tags = reading_list.reading_list_tags.get_selected_values(
            constants.ReadingListTagFilterType.EXCLUDE
        )

        assert included_tags == [tag1.slug]
        assert excluded_tags == [tag2.slug]

    def test_associate_reading_list_with_tag_slugs(self, user):
        reading_list = ReadingListFactory(user=user)
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        tag3 = TagFactory(user=user)
        tag4 = TagFactory(user=user)
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag1,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag3,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )
        ReadingListTag.objects.create(
            reading_list=reading_list,
            tag=tag4,
            filter_type=constants.ReadingListTagFilterType.EXCLUDE,
        )

        ReadingListTag.objects.associate_reading_list_with_tags(
            reading_list,
            [tag2, tag3],
            constants.ReadingListTagFilterType.INCLUDE,
        )

        reading_list.refresh_from_db()
        assert list(reading_list.reading_list_tags.values_list("tag__slug", "filter_type")) == [
            (tag2.slug, constants.ReadingListTagFilterType.INCLUDE),
            (tag3.slug, constants.ReadingListTagFilterType.INCLUDE),
            (tag4.slug, constants.ReadingListTagFilterType.EXCLUDE),
        ]
        assert Tag.objects.count() == 4
