from typing import TypedDict, Literal

from django.conf import settings
from django.template import Context
from django.template.base import Template


class PageForFeedSubscriptionCtx(TypedDict):
    feed_links: str


class FeedRenderingCtx(TypedDict):
    item_link: str


def get_article_fixture_content(name: str):
    file_path = settings.APPS_DIR / "feeds/tests/fixtures/articles" / name
    with file_path.open() as f:
        return f.read()


def get_feed_fixture_content(name: Literal["sample_rss.xml", "sample_atom.xml", "attack_feed.xml"], rendering_values: FeedRenderingCtx | None = None):
    rendering_values = rendering_values or {"item_link": "http://example.org/entry/3"}
    file_path = settings.APPS_DIR / "feeds/tests/fixtures/feeds" / name
    with file_path.open() as f:
        template_data =  f.read()

    return Template(template_data).render(Context(rendering_values))


def get_page_for_feed_subscription_content(rendering_values: PageForFeedSubscriptionCtx):
    file_path = settings.APPS_DIR / "feeds/tests/fixtures/feeds/html_template_to_find_feed_link.html"
    with file_path.open() as f:
        template_data = f.read()

    return Template(template_data).render(Context(rendering_values))

