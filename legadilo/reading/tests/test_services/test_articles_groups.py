#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from legadilo.reading.models import Article, ArticlesGroup
from legadilo.reading.services.articles_groups import SaveArticlesGroupResult, save_articles_group
from legadilo.reading.tests.factories import ArticleFactory, ArticlesGroupFactory, TagFactory


@pytest.mark.django_db
class TestSaveArticlesGroup:
    def test_save_articles_group_success(self, user, django_assert_num_queries, httpx_mock):
        tag = TagFactory(title="existing-tag", user=user)
        httpx_mock.add_response(text="Data", url="https://example.com/article-with-content/")

        with django_assert_num_queries(22):
            result = save_articles_group(
                user,
                "My new group",
                "Some description",
                tag_slugs=[tag.slug, "new-tag"],
                urls=[
                    "https://example.com/article-with-content/",
                ],
            )

        assert result.success
        assert ArticlesGroup.objects.count() == 1
        new_group = ArticlesGroup.objects.get(title="My new group")
        new_article = Article.objects.get(url="https://example.com/article-with-content/")
        assert new_group.user == user
        assert new_group.title == "My new group"
        assert new_group.description == "Some description"
        assert new_group.slug == "my-new-group"
        assert set(new_group.articles.values_list("id", "group_order")) == {
            (new_article.id, 1),
        }
        assert set(new_article.tags.values_list("slug", flat=True)) == {"existing-tag", "new-tag"}
        assert result == SaveArticlesGroupResult(
            group=new_group,
            articles_with_fetch_errors=(),
            articles_linked_to_other_group=(),
        )

    def test_save_articles_group_articles_with_error(
        self, user, django_assert_num_queries, httpx_mock
    ):
        other_group = ArticlesGroupFactory(user=user)
        article_already_linked_to_other_group = ArticleFactory(user=user)
        other_group.articles.add(article_already_linked_to_other_group)
        httpx_mock.add_response(text="", url=article_already_linked_to_other_group.url)
        httpx_mock.add_response(text="Data", url="https://example.com/article-with-content/")
        httpx_mock.add_response(text="", url="https://example.com/articles-without-content/")

        with django_assert_num_queries(23):
            result = save_articles_group(
                user,
                "My new group",
                "Some description",
                tag_slugs=["new-tags"],
                urls=[
                    "https://example.com/article-with-content/",
                    "https://example.com/articles-without-content/",
                    article_already_linked_to_other_group.url,
                ],
            )

        assert not result.success
        assert ArticlesGroup.objects.count() == 2
        article_already_linked_to_other_group.refresh_from_db()
        new_group = ArticlesGroup.objects.get(title="My new group")
        new_article = Article.objects.get(url="https://example.com/article-with-content/")
        empty_article = Article.objects.get(url="https://example.com/articles-without-content/")
        assert set(new_group.articles.values_list("id", "group_order")) == {
            (new_article.id, 1),
            (empty_article.id, 2),
        }
        assert result == SaveArticlesGroupResult(
            group=new_group,
            articles_with_fetch_errors=(empty_article,),
            articles_linked_to_other_group=(article_already_linked_to_other_group,),
        )
