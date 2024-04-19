from legadilo.feeds.models import ReadingList


def get_js_cfg_from_reading_list(reading_list: ReadingList):
    return {"is_reading_on_scroll_enabled": reading_list.enable_reading_on_scroll}
