from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

from django.db.models import TextChoices
from django.http import HttpRequest


def create_path_converter_from_enum(enum_type: type[TextChoices]) -> type:
    names = "|".join(enum_type.names)

    class FromEnumPathConverter:
        regex = rf"({names})"

        def to_python(self, value: str) -> TextChoices:
            return enum_type(value)

        def to_url(self, value: TextChoices) -> str:
            return str(value)

    return FromEnumPathConverter


def validate_referer_url(request: HttpRequest, fallback_url: str) -> str:
    referer = request.headers.get("Referer")
    if referer and _is_absolute_request_to_us(request, referer):
        return referer

    return fallback_url


def _is_absolute_request_to_us(request: HttpRequest, url: str) -> bool:
    return url.startswith(f"{request.scheme}://{request.get_host()}")


def _is_relative_request(url: str) -> bool:
    parsed_path = urlparse(url).path
    return url.startswith("/") and url.startswith(parsed_path)


def validate_from_url(request: HttpRequest, from_url: str | None, fallback_url: str):
    if not from_url:
        return fallback_url

    if _is_absolute_request_to_us(request, from_url) or _is_relative_request(from_url):
        return from_url

    return fallback_url


def add_query_params(url: str, params: dict[str, list[str]]) -> str:
    url_fragments = list(urlsplit(url))
    query = parse_qs(url_fragments[3])
    query.update(params)
    url_fragments[3] = urlencode(query, doseq=True)
    return urlunsplit(url_fragments)


def pop_query_param(url: str, param: str) -> tuple[str, str | None]:
    url_fragments = list(urlsplit(url))
    query = parse_qs(url_fragments[3])
    read_param = query.pop(param, [])
    url_fragments[3] = urlencode(query, doseq=True)
    return urlunsplit(url_fragments), next(iter(read_param), None)
