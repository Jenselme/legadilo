import re
from typing import Any
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import HttpRequest
from django.utils.deconstruct import deconstructible
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema

from legadilo.utils.security import full_sanitize


@deconstructible
class JsonSchemaValidator:
    def __init__(self, schema):
        self._schema = schema

    def __call__(self, value):
        try:
            validate_json_schema(value, self._schema)
        except JsonSchemaValidationError as e:
            raise ValidationError(str(e)) from e


list_of_strings_json_schema_validator = JsonSchemaValidator({
    "type": "array",
    "items": {"type": "string"},
})


def language_code_validator(value: Any):
    if not value or not isinstance(value, str):
        raise ValidationError("Value must be a string")

    if len(value) == 2 and re.match(r"[a-z]{2}", value.lower()):  # noqa: PLR2004 Magic value used in comparison
        return

    if len(value) == 5 and re.match(r"[a-z]{2}[_-][a-z]{2}", value.lower()):  # noqa: PLR2004 Magic value used in comparison
        return

    raise ValidationError("Language code is invalid")


def get_page_number_from_request(request: HttpRequest) -> int:
    raw_page = request.GET.get("page", 1)

    try:
        return int(raw_page)
    except (TypeError, ValueError):
        return 1


def is_url_valid(url: str | None) -> bool:
    if not url:
        return False

    validator = URLValidator(schemes=["http", "https"])
    url_fields = list(urlsplit(url))
    # Assume HTTPS if no scheme.
    if not url_fields[0]:
        url_fields[0] = "https"

    url_with_scheme = urlunsplit(url_fields)
    try:
        validator(url_with_scheme)
    except ValidationError:
        return False

    return True


def normalize_url(base_url: str, url_to_normalize: str) -> str:
    if not is_url_valid(url_to_normalize):
        return _build_normalized_url_from_invalid_url(base_url, url_to_normalize)

    if url_to_normalize.startswith("http://") or url_to_normalize.startswith("https://"):
        return url_to_normalize

    if url_to_normalize.startswith("//"):
        return f"https:{url_to_normalize}"

    raise ValueError(f"Failed to normalize URL: {url_to_normalize}")


def _build_normalized_url_from_invalid_url(base_url: str, url_to_normalize: str) -> str:
    sanitized_url = full_sanitize(url_to_normalize)
    parsed_base_url = urlparse(base_url)
    if sanitized_url.startswith("/"):
        normalized_url = urljoin(
            f"{parsed_base_url.scheme}://{parsed_base_url.netloc}", sanitized_url
        )
    else:
        normalized_url = f"{parsed_base_url.scheme}://{sanitized_url}"

    if is_url_valid(normalized_url):
        return normalized_url

    raise ValueError(f"Failed to normalize URL: {url_to_normalize}")
