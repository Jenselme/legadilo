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
