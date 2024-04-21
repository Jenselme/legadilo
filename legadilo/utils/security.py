from typing import AbstractSet

import nh3


def full_sanitize(data: str) -> str:
    return nh3.clean(data, tags=set(), strip_comments=True)


def sanitize_keep_safe_tags(
    data: str, extra_tags_to_cleanup: AbstractSet[str] = frozenset()
) -> str:
    allowed_tags = nh3.ALLOWED_TAGS - extra_tags_to_cleanup

    return nh3.clean(
        data,
        tags=allowed_tags,
        attributes=nh3.ALLOWED_ATTRIBUTES,
        strip_comments=True,
    )
