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

import pytest

from legadilo.reading import constants
from legadilo.reading.models import ArticleTag, Tag
from legadilo.reading.tests.factories import ArticleFactory, TagFactory


@pytest.mark.django_db()
class TestTagManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag1 = TagFactory(user=user)
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


@pytest.mark.django_db()
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
        article_tags = ArticleTag.objects.get_queryset().for_reading_list()

        assert list(article_tags) == [self.article_tag1, self.article_tag3]

    def test_for_articles_and_tags(self):
        article_tags = list(
            ArticleTag.objects.get_queryset().for_articles_and_tags(
                [self.article], [self.tag1, self.tag2]
            )
        )

        assert article_tags == [self.article_tag1, self.article_tag2]

    def test_for_deleted_links(self):
        article_tags_marked_as_deleted = list(
            ArticleTag.objects.get_queryset().for_deleted_links([
                (self.article.id, self.tag1.id),
                (self.article.id, self.tag2.id),
                (self.article.id, self.tag3.id),
            ])
        )

        assert article_tags_marked_as_deleted == [self.article_tag2]


@pytest.mark.django_db()
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
