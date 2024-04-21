from collections.abc import Callable
from unittest.mock import ANY

import pytest

from legadilo.feeds.tests.fixtures import get_fixture_file_content
from legadilo.feeds.utils.article_fetching import ArticleData, get_article_from_url
from legadilo.utils.time import utcdt


@pytest.mark.asyncio()
async def test_get_article_from_url(httpx_mock):
    url = "https://www.example.com/posts/en/1-super-article/"
    httpx_mock.add_response(url=url, text=get_fixture_file_content("sample_blog_article.html"))

    article_data = await get_article_from_url(url)

    assert article_data == ArticleData(
        external_article_id="",
        source_title="Super blog",
        title="On the 3 musketeers",
        summary="I just wrote a new book, I’ll hope you will like it! Here are some thoughts on it.",
        content="""<article>

<div>
<p>
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nunc porttitor dolor in justo pharetra suscipit. Vestibulum hendrerit felis id ex gravida egestas. Sed tempus placerat nibh. Proin faucibus bibendum magna in ultricies. Fusce feugiat sagittis odio a gravida. Pellentesque dignissim lorem quis eros placerat ullamcorper nec ut quam. Curabitur non tortor a justo hendrerit vehicula in a neque. Mauris vitae mi ante. Aenean et efficitur massa. Donec nec scelerisque lectus, eu malesuada urna. Aenean at dignissim purus. Praesent et tellus non ligula mollis commodo id sed felis. Phasellus fringilla non libero vitae efficitur.
                    </p>
<p>
                        Vivamus eu ornare ligula. Sed ac justo eget metus tempus venenatis. Aenean ante arcu, dignissim sed bibendum nec, commodo ut tellus. Donec rhoncus leo a enim volutpat, ut porttitor risus sodales. Proin sit amet sapien vitae felis mollis luctus. Morbi malesuada nec quam sed facilisis. Vivamus urna quam, sagittis at eros vitae, porta eleifend orci. Aliquam nec velit enim. Suspendisse egestas pulvinar volutpat. Pellentesque nec sem eget nunc facilisis porta. Ut eleifend mi sed laoreet sollicitudin. Sed sagittis nibh eget quam luctus facilisis.
                    </p>
<p>
                        Vestibulum eu nibh ullamcorper, luctus tortor eget, semper arcu. Curabitur id cursus urna, eu accumsan mi. Curabitur ornare elit vitae quam tempor egestas. Maecenas viverra malesuada sapien non blandit. Sed luctus pellentesque nulla eu pretium. Cras iaculis interdum interdum. Ut in metus purus. Aliquam id pretium velit, eu tempus tellus.
                    </p>
<div>
<p>Opinion</p>
<p>You may disagree</p>
</div>
</div>
<div>
<p>
<a href="//www.example.com/tag/Musketeers.html" rel="noopener noreferrer">Musketeers</a>
</p>
</div>
</article>""",
        authors=["Alexandre Dumas"],
        contributors=[],
        tags=["Musketeers"],
        link="//www.example.com/posts/en/1-super-article/",
        published_at=utcdt(2024, 2, 26, 23, 0),
        updated_at=utcdt(2024, 3, 8, 23, 0),
    )


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
async def test_get_article_from_url_process_fixture(process_fn: Callable[[str], str], httpx_mock):
    url = "https://www.example.com/posts/en/1-super-article/"
    httpx_mock.add_response(
        url=url, text=process_fn(get_fixture_file_content("sample_blog_article.html"))
    )

    article_data = await get_article_from_url(url)

    assert article_data == ArticleData(
        external_article_id="",
        source_title="Super blog",
        title="On the 3 musketeers",
        summary="I just wrote a new book, I’ll hope you will like it! Here are some thoughts on it.",
        content=ANY,
        authors=["Alexandre Dumas"],
        contributors=[],
        tags=["Musketeers"],
        link="//www.example.com/posts/en/1-super-article/",
        published_at=utcdt(2024, 2, 26, 23, 0),
        updated_at=utcdt(2024, 3, 8, 23, 0),
    )
    assert len(article_data.content) > 10
