from __future__ import annotations

from dateutil.relativedelta import relativedelta
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class SupportedFeedType(TextChoices):
    rss090 = "rss090", "RSS 0.90"
    rss091n = "rss091n", "RSS 0.91 (Netscape)"
    rss091u = "rss091u", "RSS 0.91 (Userland)"
    rss092 = "rss092", "RSS 0.92"
    rss093 = "rss093", "RSS 0.93"
    rss094 = "rss094", "RSS 0.94"
    rss20 = "rss20", "RSS 2.0"
    rss10 = "rss10", "RSS 1.0"
    rss = "rss", "RSS (unknown version)"
    atom01 = "atom01", "Atom 0.1"
    atom02 = "atom02", "Atom 0.2"
    atom03 = "atom03", "Atom 0.3"
    atom10 = "atom10", "Atom 1.0"
    atom = "atom", "Atom (unknown version)"
    cdf = "cdf", "CDF"
    json1 = "json1", "JSON 1"


class FeedRefreshDelays(TextChoices):
    pass
    HOURLY = "HOURLY", _("Hourly")
    BIHOURLY = "BIHOURLY", _("Bihourly")
    EVERY_MORNING = "EVERY_MORNING", _("Every Morning")
    DAILY_AT_NOON = "DAILY_AT_NOON", _("Daily at Noon")
    EVERY_EVENING = "EVERY_EVENING", _("Every Evening")
    ON_MONDAYS = "ON_MONDAYS", _("On Mondays")
    ON_THURSDAYS = "ON_THURSDAYS", _("On Thursdays")
    TWICE_A_WEEK = "TWICE_A_WEEK", _("Twice a week")
    FIRST_DAY_OF_THE_MONTH = "FIRST_DAY_OF_THE_MONTH", _("First Day of the Month")
    MIDDLE_OF_THE_MONTH = "MIDDLE_OF_THE_MONTH", _("Middle Day of the Month")
    END_OF_THE_MONTH = "END_OF_THE_MONTH", _("End of the Month")
    THRICE_A_MONTH = "THRICE_A_MONTH", _("Thrice a month")


class FeedUpdateStatus(TextChoices):
    SUCCESS = "SUCCESS", _("Success")
    FAILURE = "FAILURE", _("Failure")
    NOT_MODIFIED = "NOT_MODIFIED", _("Not Modified")


FEED_ERRORS_TIME_WINDOW = relativedelta(weeks=2)
HTTP_TIMEOUT = 20  # In seconds.
HTTP_TIMEOUT_CMD_CTX = 300  # In seconds.
MAX_FEED_FILE_SIZE = 10 * 1024 * 1024  # 10MiB in bytes.
FEED_TITLE_MAX_LENGTH = 255
