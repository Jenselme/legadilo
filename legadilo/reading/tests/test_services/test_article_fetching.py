# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
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

from collections.abc import Callable
from typing import Any

import pytest

from legadilo.reading.services.article_fetching import ArticleData, get_article_from_url
from legadilo.reading.tests.fixtures import get_article_fixture_content
from legadilo.utils.testing import serialize_for_snapshot


def test_get_article_from_url(httpx_mock, snapshot):
    url = "https://www.example.com/posts/en/1-super-article/"
    httpx_mock.add_response(url=url, text=get_article_fixture_content("sample_blog_article.html"))

    article_data = get_article_from_url(url)

    snapshot.assert_match(serialize_for_snapshot(article_data), "article_data.json")


@pytest.mark.parametrize(
    "fixture_file",
    ["htm_redirection_invalid_http_equiv.html", "html_redirection.html"],
)
def test_get_article_from_url_with_http_equiv(fixture_file, httpx_mock):
    url = "https://newsletter.com/article/1"
    httpx_mock.add_response(url=url, text=get_article_fixture_content(fixture_file))
    article_url = "https://example.com/article/redirected-article/"
    httpx_mock.add_response(
        url=article_url, text=get_article_fixture_content("sample_blog_article.html")
    )

    article_data = get_article_from_url(url)

    assert article_data.url == "https://www.example.com/posts/en/1-super-article/"
    assert article_data.title == "On the 3 musketeers"


@pytest.mark.parametrize(
    ("fixture_file", "expected_starts_with"),
    [
        (
            "multiple_articles_tags.html",
            "<article>",
        ),
        ("multiple_articles_tags_identify_class.html", "<article>"),
        ("multiple_articles_tags_identify_section_by_class.html", "\n<div>\n<p>\n"),
    ],
)
def test_get_article_from_url_weird_content(fixture_file, expected_starts_with, httpx_mock):
    url = "https://www.example.com/posts/en/1-super-article/"
    httpx_mock.add_response(url=url, text=get_article_fixture_content(fixture_file))

    article_data = get_article_from_url(url)

    assert article_data.title == "On the 3 musketeers"
    assert article_data.content.startswith(expected_starts_with)
    assert "Lorem ipsum dolor sit amet" in article_data.content


@pytest.mark.parametrize(
    "process_fn",
    [
        pytest.param(
            lambda content: content.replace("<article>", "").replace("</article>", ""),
            id="no-article-tag",
        ),
    ],
)
def test_get_article_from_url_process_fixture(
    process_fn: Callable[[str], str], httpx_mock, snapshot
):
    url = "https://www.example.com/posts/en/1-super-article/"
    httpx_mock.add_response(
        url=url, text=process_fn(get_article_fixture_content("sample_blog_article.html"))
    )

    article_data = get_article_from_url(url)

    snapshot.assert_match(serialize_for_snapshot(article_data), "article_data.json")


@pytest.mark.parametrize(
    "parameters",
    [
        pytest.param(
            {
                "external_article_id": "<p>external article id",
                "source_title": "<p>source article title</p>",
                "title": "<p>Title</p>",
                "summary": """<p>Summary <span>?</span> <img src="/toto" /> </p>""",
                "content": """<p>C <span>?</span> <img src="/t" /> <script>alert()</script></p>""",
                "authors": ["<span>me</span>"],
                "contributors": ["<span>me</span>"],
                "tags": ["<span>tag</span>"],
                "url": "https://example.com/articles/1",
                "preview_picture_url": "https://example.com/articles/1.png",
                "preview_picture_alt": "<p>Hi there!</p>",
                "published_at": None,
                "updated_at": None,
                "language": "<span>en</span>",
                "read_at": None,
                "is_favorite": False,
            },
            id="full-with-required-escaping",
        ),
        pytest.param(
            {
                "external_article_id": "<p>external article id",
                "source_title": "",
                "title": "",
                "summary": """<p>Summary <span>?</span> <img src="/toto" /> </p>""",
                "content": """<p>C <span>?</span> <img src="/t" /> <script>alert()</script></p>""",
                "authors": ["<span>me</span>"],
                "contributors": ["<span>me</span>"],
                "tags": ["<span>tag</span>"],
                "url": "https://example.com/articles/1",
                "preview_picture_url": "https://example.com/articles/1.png",
                "preview_picture_alt": "<p>Hi there!</p>",
                "published_at": None,
                "updated_at": None,
                "language": "<span>en</span>",
                "read_at": None,
                "is_favorite": False,
            },
            id="title-missing",
        ),
        pytest.param(
            {
                "external_article_id": "<p>external article id",
                "source_title": "<p>source article title</p>",
                "title": "<p>Title</p>",
                "summary": "",
                "content": """<p>C <span>?</span> <img src="/t" /> <script>alert()</script></p>""",
                "authors": ["<span>me</span>"],
                "contributors": ["<span>me</span>"],
                "tags": ["<span>tag</span>"],
                "url": "https://example.com/articles/1",
                "preview_picture_url": "https://example.com/articles/1.png",
                "preview_picture_alt": "<p>Hi there!</p>",
                "published_at": None,
                "updated_at": None,
                "language": "<span>en</span>",
                "read_at": None,
                "is_favorite": False,
            },
            id="summary-missing",
        ),
        pytest.param(
            {
                "external_article_id": "<p>external article id",
                "source_title": "<p>source article title</p>",
                "title": "<p>Title</p>",
                "summary": """<p><a href="/relative">Link 1</a><a href="https://example.com/abs">Link 1</a></p>""",  # noqa: E501
                "content": """<p><a href="/relative">Link 1</a><a href="https://example.com/abs">Link 1</a><img src="/relative.png" /><img src="https://example.com/image.png" /></p>""",  # noqa: E501
                "authors": ["<span>me</span>"],
                "contributors": ["<span>me</span>"],
                "tags": ["<span>tag</span>"],
                "url": "https://example.com/articles/1",
                "preview_picture_url": "https://example.com/articles/1.png",
                "preview_picture_alt": "<p>Hi there!</p>",
                "published_at": None,
                "updated_at": None,
                "language": "<span>en</span>",
                "read_at": None,
                "is_favorite": False,
            },
            id="link-correction",
        ),
        pytest.param(
            {
                "external_article_id": "<p>external article id",
                "source_title": "<p>source article title</p>",
                "title": "<p>Title</p>",
                "summary": """<p><a href="/relative">Link 1</a><a href="https://example.com/abs">Link 1</a></p>""",  # noqa: E501
                "content": """
                <h1>Some header</h1>
                <h2 id="test">This one has an id</h2>
                <p>Some text</p>
                <h2>This one <em>has HTML</em> in <script>it</script></h2>
                <h1>Another root title</h1>
                """,
                "authors": ["<span>me</span>"],
                "contributors": ["<span>me</span>"],
                "tags": ["<span>tag</span>"],
                "url": "https://example.com/articles/1",
                "preview_picture_url": "https://example.com/articles/1.png",
                "preview_picture_alt": "<p>Hi there!</p>",
                "published_at": None,
                "updated_at": None,
                "language": "<span>en</span>",
                "read_at": None,
                "is_favorite": False,
            },
            id="with-headers",
        ),
    ],
)
def test_build_article_data(parameters: dict[str, Any], snapshot):
    article_data = ArticleData(**parameters)

    snapshot.assert_match(serialize_for_snapshot(article_data), "article_data.json")
