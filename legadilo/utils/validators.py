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

import re
from typing import Any
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import HttpRequest
from django.utils.deconstruct import deconstructible
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema
from nh3 import is_html

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

table_of_content_json_schema_validator = JsonSchemaValidator({
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "text": {"type": "string"},
            "level": {"type": "integer"},
            "children": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text": {"type": "string"},
                        "level": {"type": "integer"},
                    },
                    "additionalProperties": False,
                    "required": ["id", "text", "level"],
                },
            },
        },
        "additionalProperties": False,
        "required": ["id", "text", "level"],
    },
})


def language_code_validator(value: Any):
    if not value or not isinstance(value, str):
        raise ValidationError("Value must be a string")

    # To catch 'fr', 'de', …
    if len(value) == 2 and re.match(r"[a-z]{2}", value.lower()):  # noqa: PLR2004 Magic value used in comparison
        return

    # To catch 'fr-FR', 'en_US', …
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
    """Normalize HTTP URLs.

    Any links that's not HTTP(S) (like FTP, email…) or page anchors will be left untouched.
    If only the protocol is missing, we will add https in front of it.
    If the URL is relative, we will make it absolute. If it contains invalid characters, we will
    escape them. We will preserve query strings.
    See the test suite for a full look at supported cases.
    """
    if _is_not_potential_http_url(url_to_normalize):
        return url_to_normalize

    if not is_url_valid(url_to_normalize):
        return _build_normalized_url_from_invalid_url(base_url, url_to_normalize)

    if url_to_normalize.startswith("http://") or url_to_normalize.startswith("https://"):
        return url_to_normalize

    if url_to_normalize.startswith("//"):
        return f"https:{url_to_normalize}"

    raise ValueError(f"Failed to normalize URL: {url_to_normalize}")


def _is_not_potential_http_url(url: str) -> bool:
    invalid_prefixes = {
        "#",  # anchor
        "gemini://",  # Other protocol
        "ftp://",  # Other protocol
        "mailto:",  # email
        "data:",  # base64
    }
    return any(url.startswith(invalid_prefix) for invalid_prefix in invalid_prefixes)


def _build_normalized_url_from_invalid_url(base_url: str, url_to_normalize: str) -> str:  # noqa: C901,PLR0912 toto complex
    exception = ValueError(f"Failed to normalize URL: {url_to_normalize}")
    compiled_starts_with_scheme = re.compile(r"^https?://")
    if not url_to_normalize:
        raise exception
    if (
        " " in url_to_normalize
        and not url_to_normalize.startswith("/")
        and not url_to_normalize.startswith("?")
        and not compiled_starts_with_scheme.match(url_to_normalize)
    ):
        raise exception

    sanitized_url = url_to_normalize
    if "\\" in sanitized_url:
        sanitized_url = sanitized_url.replace("\\", "/")
    if " " in sanitized_url:
        sanitized_url = sanitized_url.replace(" ", "%20")
    if is_html(sanitized_url):
        sanitized_url = full_sanitize(sanitized_url)

    parsed_base_url = urlparse(base_url)
    if sanitized_url.startswith("/"):
        normalized_url = urljoin(
            f"{parsed_base_url.scheme}://{parsed_base_url.netloc}", sanitized_url
        )
    elif sanitized_url.startswith("?"):
        normalized_url = urljoin(
            f"{parsed_base_url.scheme}://{parsed_base_url.netloc}", f"/{sanitized_url}"
        )
    elif sanitized_url.startswith(".."):
        # It's a unix like relative link. Let's try to resolve it and go one step above the base
        # URL.
        base_path_parts = base_url.split("/")
        if base_url.endswith("/"):
            base_path_parts.pop()
        sanitized_url_parts = sanitized_url.split("/")
        if sanitized_url.endswith("/"):
            sanitized_url_parts.pop()
        target_path = base_path_parts[:-1]
        if len(sanitized_url_parts) > 1:
            target_path.extend(sanitized_url_parts[1:])
        normalized_url = urljoin(
            f"{parsed_base_url.scheme}://{parsed_base_url.netloc}", "/".join(target_path)
        )
        if base_url.endswith("/") and not normalized_url.startswith("/"):
            normalized_url += "/"
    elif (
        not compiled_starts_with_scheme.match(sanitized_url)
        and parsed_base_url.netloc not in sanitized_url
    ):
        # Relative URL but without a starting /
        normalized_url = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}/{sanitized_url}"
    elif not compiled_starts_with_scheme.match(sanitized_url):
        normalized_url = f"{parsed_base_url.scheme}://{sanitized_url}"
    else:
        normalized_url = sanitized_url

    if is_url_valid(normalized_url):
        return normalized_url

    raise exception
