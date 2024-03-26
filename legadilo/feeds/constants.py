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


class ReadStatus(TextChoices):
    ALL = "ALL", _("All")
    ONLY_UNREAD = "ONLY_UNREAD", _("Only unread")
    ONLY_READ = "ONLY_READ", _("Only read")


class FavoriteStatus(TextChoices):
    ALL = "ALL", _("All")
    ONLY_FAVORITE = "ONLY_FAVORITE", _("Only favorite")
    ONLY_NON_FAVORITE = "ONLY_NON_FAVORITE", _("Only non favorite")


class ArticlesMaxAgeUnit(TextChoices):
    UNSET = "UNSET", _("Unset")
    HOURS = "HOURS", _("Hour(s)")
    DAYS = "DAYS", _("Day(s)")
    WEEKS = "WEEKS", _("Week(s)")
    MONTHS = "MONTHS", _("Month(s)")


class TaggingReason(TextChoices):
    ADDED_MANUALLY = "ADDED_MANUALLY", _("Added manually")
    FROM_FEED = "FROM_FEED", _("From feed")


FEED_ERRORS_TIME_WINDOW = relativedelta(weeks=2)
HTTP_TIMEOUT = 20  # In seconds.
HTTP_TIMEOUT_CMD_CTX = 300  # In seconds.
MAX_FEED_FILE_SIZE = 1024 * 1024  # 1MiB in bytes.
