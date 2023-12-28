import nh3


def full_sanitize(data: str) -> str:
    return nh3.clean(data, tags=set(), strip_comments=True)
