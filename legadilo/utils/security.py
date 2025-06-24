# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections.abc import Set

import nh3

DEFAULT_ALLOWED_ATTRIBUTES = {
    **nh3.ALLOWED_ATTRIBUTES,
    "img": {"src", "alt"},
}


def full_sanitize(data: str) -> str:
    """Remove all HTML tags from the input string."""
    return nh3.clean(data, tags=set(), strip_comments=True)


def sanitize_keep_safe_tags(data: str, extra_tags_to_cleanup: Set[str] = frozenset()) -> str:
    """Remove HTML tags and attribute that are not considered safe.

    You can pass a set of extra tags to remove to adapt it to your usage (for instance to also clean
    img tag).
    """
    allowed_tags = nh3.ALLOWED_TAGS - extra_tags_to_cleanup

    return nh3.clean(
        data,
        tags=allowed_tags,
        attributes=_add_attribute_to_allowed_attributes(DEFAULT_ALLOWED_ATTRIBUTES, {"id"}),
        url_schemes=nh3.ALLOWED_URL_SCHEMES | {"data"},
        strip_comments=True,
    )


def _add_attribute_to_allowed_attributes(
    allowed_attributes: dict[str, set[str]], attributes_to_add: set[str]
) -> dict[str, set[str]]:
    extended_allowed_attributes = {
        tag: allowed_attr.union(attributes_to_add)
        for tag, allowed_attr in allowed_attributes.items()
    }
    for tag in nh3.ALLOWED_TAGS:
        if tag not in extended_allowed_attributes:
            extended_allowed_attributes[tag] = attributes_to_add

    return extended_allowed_attributes
