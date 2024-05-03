from django.urls import reverse

from legadilo.feeds import constants
from legadilo.feeds.models import ReadingList
from legadilo.utils.urls import validate_from_url


def get_js_cfg_from_reading_list(reading_list: ReadingList):
    return {
        "is_reading_on_scroll_enabled": reading_list.enable_reading_on_scroll,
        "auto_refresh_interval": reading_list.auto_refresh_interval,
        "articles_list_min_refresh_timeout": constants.ARTICLES_LIST_MIN_REFRESH_TIMEOUT,
    }


def get_from_url_for_article_details(request, query_dict) -> str:
    return validate_from_url(
        request, query_dict.get("from_url"), reverse("feeds:default_reading_list")
    )
