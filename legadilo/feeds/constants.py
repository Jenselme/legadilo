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


class FeedUpdateStatus(TextChoices):
    SUCCESS = "SUCCESS", _("Success")
    FAILURE = "FAILURE", _("Failure")
    NOT_MODIFIED = "NOT_MODIFIED", _("Not Modified")


class ReadStatus(TextChoices):
    ALL = "ALL", _("All")
    ONLY_UNREAD = "ONLY_UNREAD", _("Only unread")
    ONLY_READ = "ONLY_READ", _("Only read")


class FavoriteStatus(TextChoices):
    ALL = "ALL", _("All")
    ONLY_FAVORITE = "ONLY_FAVORITE", _("Only favorite")
    ONLY_NON_FAVORITE = "ONLY_NON_FAVORITE", _("Only non favorite")


class ForLaterStatus(TextChoices):
    ALL = "ALL", _("All")
    ONLY_FOR_LATER = "ONLY_FOR_LATER", _("Only for later")
    ONLY_NOT_FOR_LATER = "ONLY_NOT_FOR_LATER", _("Only for not later")


class ArticlesMaxAgeUnit(TextChoices):
    UNSET = "UNSET", _("Unset")
    HOURS = "HOURS", _("Hour(s)")
    DAYS = "DAYS", _("Day(s)")
    WEEKS = "WEEKS", _("Week(s)")
    MONTHS = "MONTHS", _("Month(s)")


class ArticlesReadingTimeOperator(TextChoices):
    UNSET = "UNSET", _("Unset")
    MORE_THAN = "MORE_THAN", _("More than than")
    LESS_THAN = "LESS_THAN", _("Less than than")


class TaggingReason(TextChoices):
    ADDED_MANUALLY = "ADDED_MANUALLY", _("Added manually")
    FROM_FEED = "FROM_FEED", _("From feed")
    # Used to mark a tag initially associated because of a feed but manually deleted by the user.
    # We don't want it to come back when we update the article!
    DELETED = "DELETED", _("Deleted")


class ReadingListTagFilterType(TextChoices):
    INCLUDE = "INCLUDE", _("Include")
    EXCLUDE = "EXCLUDE", _("Exclude")


class ReadingListTagOperator(TextChoices):
    ALL = "ALL", _("All")
    ANY = "ANY", _("Any")


class UpdateArticleActions(TextChoices):
    MARK_AS_FAVORITE = "MARK_AS_FAVORITE", _("Mark as favorite")
    UNMARK_AS_FAVORITE = "UNMARK_AS_FAVORITE", _("Unmark as favorite")
    MARK_AS_READ = "MARK_AS_READ", _("Mark as read")
    MARK_AS_UNREAD = "MARK_AS_UNREAD", _("Mark as unread")
    MARK_AS_OPENED = "MARK_AS_OPENED", _("Mark as opened")
    MARK_AS_FOR_LATER = "MARK_AS_FOR_LATER", _("Mark as for later")
    UNMARK_AS_FOR_LATER = "UNMARK_AS_FOR_LATER", _("Unmark as for later")

    @classmethod
    def is_read_status_update(cls, update_action: UpdateArticleActions) -> bool:
        return update_action in {
            cls.MARK_AS_READ,
            cls.MARK_AS_UNREAD,
        }


class ArticleSourceType(TextChoices):
    FEED = "FEED", _("Feed")
    MANUAL = "MANUAL", _("Manual")


FEED_ERRORS_TIME_WINDOW = relativedelta(weeks=2)
HTTP_TIMEOUT = 20  # In seconds.
HTTP_TIMEOUT_CMD_CTX = 300  # In seconds.
MAX_FEED_FILE_SIZE = 10 * 1024 * 1024  # 10MiB in bytes.
MAX_ARTICLE_FILE_SIZE = 1024 * 1024  # 1MiB in bytes.
MAX_ARTICLE_PER_PAGE = 50
ARTICLE_TITLE_MAX_LENGTH = 255
ARTICLE_SOURCE_TITLE_MAX_LENGTH = 255
FEED_TITLE_MAX_LENGTH = 255
ARTICLES_LIST_MIN_REFRESH_TIMEOUT = 5 * 60  # In seconds
