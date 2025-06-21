from typing import Literal, NotRequired, TypedDict

from django.conf import settings
from django.template import Context
from django.template.base import Template


class PageForFeedSubscriptionCtx(TypedDict):
    feed_urls: NotRequired[str]


class FeedRenderingCtx(TypedDict):
    item_url: str
    media_content_variant: NotRequired[Literal["media_content_description", "media_content_title"]]


def get_feed_fixture_content(
    name: Literal[
        "sample_rss.xml", "sample_atom.xml", "sample_youtube_atom.xml", "attack_feed.xml"
    ],
    override_rendering_values: FeedRenderingCtx | None = None,
):
    default_rendering_values: FeedRenderingCtx = {"item_url": "http://example.org/entry/3"}
    override_values_to_use: FeedRenderingCtx = override_rendering_values or default_rendering_values
    rendering_values = {**default_rendering_values, **override_values_to_use}
    file_path = settings.APPS_DIR / "feeds/tests/fixtures/feeds" / name
    with file_path.open() as f:
        template_data = f.read()

    return Template(template_data).render(Context(rendering_values))


def get_page_for_feed_subscription_content(rendering_values: PageForFeedSubscriptionCtx):
    file_path = settings.APPS_DIR / "feeds/tests/fixtures/feeds/html_template_to_find_feed_url.html"
    with file_path.open() as f:
        template_data = f.read()

    return Template(template_data).render(Context(rendering_values))
