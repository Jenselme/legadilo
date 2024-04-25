import pytest

from legadilo.feeds import constants
from legadilo.feeds.models import ArticleTag, FeedTag, Tag
from legadilo.feeds.tests.factories import ArticleFactory, FeedFactory, TagFactory


@pytest.mark.django_db()
class TestTagManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag1 = TagFactory(user=user)
        self.tag2 = TagFactory(user=user)
        self.other_user_tag = TagFactory()

    def test_get_all_choices(self, user):
        choices = list(Tag.objects.get_all_choices(user))

        assert choices == [(self.tag1.slug, self.tag1.name), (self.tag2.slug, self.tag2.name)]

    def test_get_or_create_from_list(self, django_assert_num_queries, user):
        with django_assert_num_queries(4):
            tags = Tag.objects.get_or_create_from_list(
                user, [self.tag1.slug, self.other_user_tag.slug, "New tag"]
            )

        assert len(tags) == 3
        assert Tag.objects.count() == 5
        assert tags[0] == self.tag1
        assert tags[1].name == self.other_user_tag.slug
        assert tags[1].slug == self.other_user_tag.slug
        assert tags[1].user == user
        assert tags[2].name == "New tag"
        assert tags[2].slug == "new-tag"
        assert tags[2].user == user

    def test_get_or_create_from_list_no_new(self, django_assert_num_queries, user):
        with django_assert_num_queries(3):
            tags = Tag.objects.get_or_create_from_list(user, [self.tag1.slug])

        assert len(tags) == 1
        assert Tag.objects.count() == 3
        assert tags[0] == self.tag1


@pytest.mark.django_db()
class TestArticleTagQuerySet:
    def test_for_reading_list(self):
        article = ArticleFactory()
        tag1 = TagFactory(user=article.user)
        tag2 = TagFactory(user=article.user)
        tag3 = TagFactory(user=article.user)
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
    def test_associate_articles_with_tags(self, user, django_assert_num_queries):
        article1 = ArticleFactory(user=user)
        article2 = ArticleFactory(user=user)
        tag1 = TagFactory(user=user)
        tag2 = TagFactory(user=user)
        tag3 = TagFactory(user=user)
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
            ArticleTag.objects.associate_articles_with_tags(
                articles, tags, tagging_reason=constants.TaggingReason.FROM_FEED
            )

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


@pytest.mark.django_db()
class TestFeedTagManager:
    def test_associate_feed_with_tags(self):
        feed = FeedFactory()
        tag1 = TagFactory(user=feed.user)
        tag2 = TagFactory(user=feed.user)
        FeedTag.objects.create(feed=feed, tag=tag1)

        FeedTag.objects.associate_feed_with_tags(feed, [tag1, tag2])

        assert FeedTag.objects.count() == 2
