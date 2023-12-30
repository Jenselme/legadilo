from datetime import UTC, datetime

import pytest
from asgiref.sync import sync_to_async

from legadilo.feeds.models.article import Article
from legadilo.feeds.tests.factories import ArticleFactory, FeedFactory
from legadilo.feeds.utils.feed_parsing import FeedArticle


@pytest.mark.django_db(transaction=True)
class TestArticleManager:
    @pytest.mark.asyncio()
    async def test_update_and_create_articles(self):
        feed = await sync_to_async(FeedFactory)()
        existing_article = await sync_to_async(ArticleFactory)(
            feed=feed, article_feed_id=f"existing-article-feed-{feed.id}"
        )

        await Article.objects.update_or_create_from_articles_list(
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

        assert await Article.objects.acount() == 3
        await existing_article.arefresh_from_db()
        assert existing_article.title == "Article updated"

    @pytest.mark.asyncio()
    async def test_update_and_create_articles_empty_list(self):
        feed = await sync_to_async(FeedFactory)()

        await Article.objects.update_or_create_from_articles_list([], feed.id)

        assert await Article.objects.acount() == 0
