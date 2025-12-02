#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass

from django.db import transaction

from legadilo.reading.models import Article, ArticlesGroup, Tag
from legadilo.reading.services.article_fetching import (
    fetch_article_data,
)
from legadilo.users.models import User


@dataclass(frozen=True)
class SaveArticlesGroupResult:
    group: ArticlesGroup
    articles_with_fetch_errors: tuple[Article, ...]
    articles_linked_to_other_group: tuple[Article, ...]

    @property
    def success(self) -> bool:
        return not self.articles_with_fetch_errors and not self.articles_linked_to_other_group


def save_articles_group(
    user: User, title: str, description: str, tag_slugs: list[str], urls: list[str]
) -> SaveArticlesGroupResult:
    fetch_article_results = [fetch_article_data(url) for url in urls]

    with transaction.atomic():
        tags = Tag.objects.get_or_create_from_list(user, tag_slugs)
        group = ArticlesGroup.objects.create_with_tags(
            user=user,
            title=title,
            description=description,
            tags=tags,
        )
        article_save_results = Article.objects.save_from_fetch_results(
            user,
            fetch_article_results,
            tags,
            force_update=False,
        )
        article_ids_to_articles = {
            result.article.id: result.article for result in article_save_results
        }
        articles_already_linked = Article.objects.link_articles_to_group(
            group, article_ids_to_articles.values()
        )

    return SaveArticlesGroupResult(
        group=group,
        articles_with_fetch_errors=tuple(
            article
            for article in article_ids_to_articles.values()
            if not article.content and article not in articles_already_linked
        ),
        articles_linked_to_other_group=articles_already_linked,
    )
