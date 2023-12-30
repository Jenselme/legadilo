import nh3


def full_sanitize(data: str) -> str:
    return nh3.clean(data, tags=set(), strip_comments=True)


def sanitize_keep_safe_tags(data: str) -> str:
    return nh3.clean(data, tags=nh3.ALLOWED_TAGS, attributes=nh3.ALLOWED_ATTRIBUTES, strip_comments=True)
