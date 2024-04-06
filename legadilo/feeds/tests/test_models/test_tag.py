import pytest

from legadilo.feeds import constants
from legadilo.feeds.models import ArticleTag
from legadilo.feeds.tests.factories import ArticleFactory, FeedFactory, TagFactory


@pytest.mark.django_db()
class TestArticleTagQuerySet:
    def test_for_reading_list(self):
        article = ArticleFactory()
        tag1 = TagFactory(user=article.feed.user)
        tag2 = TagFactory(user=article.feed.user)
        tag3 = TagFactory(user=article.feed.user)
        ArticleTag.objects.create(
            tag=tag1, article=article, tagging_reason=constants.TaggingReason.FROM_FEED
        )
        ArticleTag.objects.create(
            tag=tag2, article=article, tagging_reason=constants.TaggingReason.DELETED
        )
        ArticleTag.objects.create(
            tag=tag3, article=article, tagging_reason=constants.TaggingReason.ADDED_MANUALLY
        )

        article_tags = ArticleTag.objects.get_queryset().for_reading_list()

        assert len(article_tags) == 2
        assert article_tags[0].name == tag1.name
        assert article_tags[0].slug == tag1.slug
        assert article_tags[1].name == tag3.name
        assert article_tags[1].slug == tag3.slug


@pytest.mark.django_db()
class TestArticleTagManager:
    def test_associate_articles_with_tags(self, django_assert_num_queries):
        feed = FeedFactory()
        article1 = ArticleFactory(feed=feed)
        article2 = ArticleFactory(feed=feed)
        tag1 = TagFactory(user=feed.user)
        tag2 = TagFactory(user=feed.user)
        tag3 = TagFactory(user=feed.user)
        articles = [article1, article2]
        # The article already has the tag, nothing must happen.
        ArticleTag.objects.create(
            article=article1, tag=tag1, tagging_reason=constants.TaggingReason.FROM_FEED
        )
        # The user deleted the tag, nothing must happen.
        ArticleTag.objects.create(
            article=article1, tag=tag2, tagging_reason=constants.TaggingReason.DELETED
        )
        # The user added a tag manually, nothing must happen.
        ArticleTag.objects.create(
            article=article1, tag=tag3, tagging_reason=constants.TaggingReason.ADDED_MANUALLY
        )
        tags = [tag1, tag2]

        with django_assert_num_queries(1):
            ArticleTag.objects.associate_articles_with_tags(articles, tags)

        created_article_tags = list(ArticleTag.objects.values("article", "tag", "tagging_reason"))
        assert created_article_tags == [
            {
                "article": article1.id,
                "tag": tag1.id,
                "tagging_reason": constants.TaggingReason.FROM_FEED,
            },
            {
                "article": article1.id,
                "tag": tag2.id,
                "tagging_reason": constants.TaggingReason.DELETED,
            },
            {
                "article": article1.id,
                "tag": tag3.id,
                "tagging_reason": constants.TaggingReason.ADDED_MANUALLY,
            },
            {
                "article": article2.id,
                "tag": tag1.id,
                "tagging_reason": constants.TaggingReason.FROM_FEED,
            },
            {
                "article": article2.id,
                "tag": tag2.id,
                "tagging_reason": constants.TaggingReason.FROM_FEED,
            },
        ]
