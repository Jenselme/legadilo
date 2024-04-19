from legadilo.feeds import constants
from legadilo.feeds.models import ReadingList


def get_js_cfg_from_reading_list(reading_list: ReadingList):
    return {
        "is_reading_on_scroll_enabled": reading_list.enable_reading_on_scroll,
        "auto_refresh_interval": reading_list.auto_refresh_interval,
        "articles_list_min_refresh_timeout": constants.ARTICLES_LIST_MIN_REFRESH_TIMEOUT,
    }
