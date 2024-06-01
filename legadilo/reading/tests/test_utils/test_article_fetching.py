from collections.abc import Callable

import pytest

from legadilo.reading.tests.fixtures import get_article_fixture_content
from legadilo.reading.utils.article_fetching import get_article_from_url
from legadilo.utils.testing import serialize_for_snapshot


@pytest.mark.asyncio()
async def test_get_article_from_url(httpx_mock, snapshot):
    url = "https://www.example.com/posts/en/1-super-article/"
    httpx_mock.add_response(url=url, text=get_article_fixture_content("sample_blog_article.html"))

    article_data = await get_article_from_url(url)

    snapshot.assert_match(serialize_for_snapshot(article_data), "article_data.json")


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "fixture_file",
    ["htm_redirection_invalid_http_equiv.html", "html_redirection.html"],
)
async def test_get_article_from_url_with_http_equiv(fixture_file, httpx_mock, snapshot):
    url = "https://newsletter.com/article/1"
    httpx_mock.add_response(url=url, text=get_article_fixture_content(fixture_file))
    article_url = "https://example.com/article/redirected-article/"
    httpx_mock.add_response(
        url=article_url, text=get_article_fixture_content("sample_blog_article.html")
    )

    article_data = await get_article_from_url(url)

    assert article_data.link == "https://www.example.com/posts/en/1-super-article/"
    assert article_data.title == "On the 3 musketeers"


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "process_fn",
    [
        pytest.param(
            lambda content: content.replace("<article>", "").replace("</article>", ""),
            id="no-article-tag",
        ),
    ],
)
async def test_get_article_from_url_process_fixture(
    process_fn: Callable[[str], str], httpx_mock, snapshot
):
    url = "https://www.example.com/posts/en/1-super-article/"
    httpx_mock.add_response(
        url=url, text=process_fn(get_article_fixture_content("sample_blog_article.html"))
    )

    article_data = await get_article_from_url(url)

    snapshot.assert_match(serialize_for_snapshot(article_data), "article_data.json")
