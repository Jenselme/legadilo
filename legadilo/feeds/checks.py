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

from django.core import checks
from django.core.checks import Error
from feedparser.api import SUPPORTED_VERSIONS as FEEDPARSER_SUPPORTED_VERSIONS

from .constants import SupportedFeedType


def check_supported_feed_types_are_supported_by_feedparser(**kwargs):
    errors = []
    # We don't support the unknown feed.
    supported_versions = set(FEEDPARSER_SUPPORTED_VERSIONS.keys()) - {""}
    if set(SupportedFeedType.names) != supported_versions:
        removed_versions = set(SupportedFeedType.names) - supported_versions
        added_versions = supported_versions - set(SupportedFeedType.names)
        errors.append(
            Error(
                "Supported feed types differ from the supported version of feedparser: "
                f"{removed_versions=}, {added_versions=}",
                id="legadilo.E002",
            )
        )

    return errors


checks.register(check_supported_feed_types_are_supported_by_feedparser)
