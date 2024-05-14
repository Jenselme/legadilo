import pytest
from jsonschema import ValidationError as JsonSchemaValidationError

from legadilo.import_export.services.wallabag import _import_wallabag_data
from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory, TagFactory


def test_import_invalid_data(user):
    with pytest.raises(JsonSchemaValidationError):
        _import_wallabag_data(user, [{"key": "value"}])


def test_import_valid_data(user):
    TagFactory(user=user, name="existing", slug="existing")
    existing_article = ArticleFactory(user=user, title="Existing title", content="Existing content")

    nb_imported_articles = _import_wallabag_data(
        user,
        [
            {
                "is_archived": 0,
                "is_starred": 0,
                "tags": ["existing", "New tag"],
                "is_public": False,
                "id": 4947,
                "title": "Some article",
                "url": "https://www.example.com/articles/podcasts/test-article.html",
                "content": "<p>Some <script>Content</script>",
                "created_at": "2024-04-19T19:18:29+02:00",
                "updated_at": "2024-04-20T19:17:54+02:00",
                "published_by": [""],
                "annotations": ["Some stuff"],
                "mimetype": r"text\/html;charset=utf-8",
                "language": "en",
                "reading_time": 29,
                "domain_name": "www.example.com",
                "preview_picture": "https://www.example.com/content/dam/images.png",
                "http_status": "200",
                "headers": {},
            },
            {
                "is_archived": 0,
                "is_starred": 0,
                "tags": [],
                "is_public": False,
                "id": 4948,
                "title": "Some article",
                "url": "https://www.example.com/articles/podcasts/test-article2.html",
                "content": "<p>Some <script>Content</script>",
                "created_at": "2024-04-19T19:18:29+02:00",
                "updated_at": "2024-04-20T19:17:54+02:00",
                "published_by": [""],
                "annotations": [],
                "mimetype": r"text\/html;charset=utf-8",
                "language": "en",
                "reading_time": 29,
                "domain_name": "www.example.com",
                "preview_picture": "https://www.example.com/content/dam/images.png",
                "http_status": "200",
                "headers": {},
            },
            {
                "is_archived": 0,
                "is_starred": 0,
                "tags": [],
                "is_public": False,
                "id": 4949,
                "title": "Some article",
                "url": existing_article.link,
                "content": "<p>Some <script>Content</script>",
                "created_at": "2024-04-19T19:18:29+02:00",
                "updated_at": "2024-04-20T19:17:54+02:00",
                "published_by": [""],
                "annotations": [],
                "mimetype": r"text\/html;charset=utf-8",
                "language": "en",
                "reading_time": 29,
                "domain_name": "www.example.com",
                "preview_picture": "https://www.example.com/content/dam/images.png",
                "http_status": "200",
                "headers": {},
            },
        ],
    )

    assert nb_imported_articles == 2
    assert Article.objects.count() == 3
    article = Article.objects.exclude(id=existing_article.id).first()
    assert article is not None
    assert article.user == user
    assert article.title == "Some article"
    assert article.link == "https://www.example.com/articles/podcasts/test-article.html"
    assert article.content == "<p>Some </p>"
    assert article.reading_time == 29
    assert article.external_article_id == "wallabag:4947"
    assert article.initial_source_type == reading_constants.ArticleSourceType.MANUAL
    assert article.initial_source_title == "www.example.com"
    assert article.annotations == ["Some stuff"]
    assert list(article.tags.values_list("name", "slug")) == [
        ("existing", "existing"),
        ("New tag", "new-tag"),
    ]
    existing_article.refresh_from_db()
    assert existing_article.title == "Existing title"
    assert existing_article.content == "Existing content"
