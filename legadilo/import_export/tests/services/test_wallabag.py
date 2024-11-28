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
from pydantic import ValidationError as PydanticValidationError

from legadilo.import_export.services.wallabag import _import_wallabag_data
from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory, TagFactory


def test_import_invalid_data(user):
    with pytest.raises(PydanticValidationError):
        _import_wallabag_data(user, [{"key": "value"}])


def test_import_valid_data(user):
    TagFactory(user=user, title="existing", slug="existing")
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
                "reading_time": 29,
                "domain_name": "www.example.com",
                "preview_picture": "https://www.example.com/content/dam/images.png",
                "http_status": "200",
                "headers": {},
            },
        ],
    )

    assert nb_imported_articles == 3
    assert Article.objects.count() == 3
    article = Article.objects.exclude(id=existing_article.id).first()
    assert article is not None
    assert article.user == user
    assert article.title == "Some article"
    assert article.link == "https://www.example.com/articles/podcasts/test-article.html"
    assert article.content == "<p>Some </p>"
    assert article.external_article_id == "wallabag:4947"
    assert article.main_source_type == reading_constants.ArticleSourceType.MANUAL
    assert article.main_source_title == "www.example.com"
    assert article.annotations == ["Some stuff"]
    assert article.language == "en"
    assert list(article.tags.values_list("title", "slug")) == [
        ("existing", "existing"),
        ("New tag", "new-tag"),
    ]
    existing_article.refresh_from_db()
    assert existing_article.title == "Existing title"
    assert existing_article.content == "Existing content"
