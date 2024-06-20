# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


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


class ReadingListOrderDirection(TextChoices):
    ASC = "ASC", _("Ascendant")
    DESC = "DESC", _("Descendant")


class UpdateArticleActions(TextChoices):
    DO_NOTHING = "DO_NOTHING", _("Do nothing")
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


MAX_ARTICLE_FILE_SIZE = 1024 * 1024  # 1MiB in bytes.
MAX_ARTICLES_PER_PAGE = 100
MAX_ARTICLES_PER_PAGE_WITH_READ_ON_SCROLL = 5 * MAX_ARTICLES_PER_PAGE
ARTICLES_ORPHANS_PERCENTAGE = 0.1  # 10%
ARTICLE_TITLE_MAX_LENGTH = 300
ARTICLE_SOURCE_TITLE_MAX_LENGTH = 300
ARTICLES_LIST_MIN_REFRESH_TIMEOUT = 5 * 60  # In seconds
MAX_SUMMARY_LENGTH = 255  # In words
EXTRA_TAGS_TO_REMOVE_FROM_SUMMARY = frozenset({"img", "pre"})
KEEP_ARTICLE_FETCH_ERROR_FOR = 60  # In days
LANGUAGE_CODE_MAX_LENGTH = 5
EXTERNAL_ARTICLE_ID_MAX_LENGTH = 512
