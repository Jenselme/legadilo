# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from django.core.exceptions import ValidationError

from ..validators import (
    get_page_number_from_request,
    is_url_valid,
    language_code_validator,
    normalize_url,
)


class TestLanguageCodeValidator:
    @pytest.mark.parametrize("code", ["", None, 12, "test", "aaaaa"])
    def test_invalid_codes(self, code):
        with pytest.raises(ValidationError):
            language_code_validator(code)

    @pytest.mark.parametrize(
        "code",
        [
            "fr",
            "en_GB",
            "en-US",
        ],
    )
    def test_valid_codes(self, code):
        assert language_code_validator(code) is None


@pytest.mark.parametrize(
    ("request_params", "expected_value"),
    [
        ({}, 1),
        ({"page": "1"}, 1),
        ({"page": "4"}, 4),
        ({"page": "aaa"}, 1),
    ],
)
def test_get_page_number(rf, request_params, expected_value):
    request = rf.get("/", request_params)

    assert get_page_number_from_request(request) == expected_value


@pytest.mark.parametrize(
    ("sample_url", "expected_is_valid"),
    [
        pytest.param("//jujens.eu/toto", True, id="url-no-scheme"),
        pytest.param("https://jujens.eu/toto", True, id="url-with-scheme"),
        pytest.param("jujens.eu/toto", False, id="url-no-scheme-no-double-slash"),
        pytest.param("/toto", False, id="path-only"),
        pytest.param("Hello world!", False, id="trash"),
        pytest.param(None, False, id="None"),
    ],
)
def test_is_url_valid(sample_url: str, expected_is_valid: bool):
    is_valid = is_url_valid(sample_url)

    assert is_valid == expected_is_valid


@pytest.mark.parametrize(
    ("base_url", "url_to_normalize", "expected_normalized_url"),
    [
        pytest.param(
            "https://example.com",
            "#toto",
            "#toto",
            id="anchor",
        ),
        pytest.param(
            "https://example.com",
            "gemini://example.com/toto",
            "gemini://example.com/toto",
            id="other-protocol",
        ),
        pytest.param(
            "https://example.com",
            "https://example.com/toto",
            "https://example.com/toto",
            id="already-full-url",
        ),
        pytest.param(
            "https://example.com",
            "//example.com/toto",
            "https://example.com/toto",
            id="url-without-scheme",
        ),
        pytest.param(
            "https://example.com",
            "example.com/toto",
            "https://example.com/toto",
            id="no-scheme-nor-double-slash",
        ),
        pytest.param("https://example.com", "/toto", "https://example.com/toto", id="path-only"),
        pytest.param(
            "https://example.com",
            "..",
            "https://example.com/",
            id="linux-link-dot-not-enough-path",
        ),
        pytest.param(
            "https://example.com/some/article/1",
            "..",
            "https://example.com/some/article",
            id="linux-link-dot",
        ),
        pytest.param(
            "https://example.com/some/article/1/",
            "..",
            "https://example.com/some/article/",
            id="linux-link-dot-trailing-slash",
        ),
        pytest.param(
            "https://example.com/some/article/1",
            "../toto",
            "https://example.com/some/article/toto",
            id="linux-link-dot-extra-path",
        ),
        pytest.param(
            "https://example.com/article/1",
            "http://example.com/photos/?gallery=Paris&photo=1",
            "http://example.com/photos/?gallery=Paris&photo=1",
            id="absolute-with-qs",
        ),
        pytest.param(
            "https://example.com/article/1",
            "/photos/?gallery=Paris&photo=1",
            "https://example.com/photos/?gallery=Paris&photo=1",
            id="relative-with-qs",
        ),
        pytest.param(
            "https://example.com/article/1",
            "?gallery=Paris&photo=1",
            "https://example.com/?gallery=Paris&photo=1",
            id="relative-with-qs-starts-with-?",
        ),
        pytest.param(
            "https://example.com/article/1",
            "http://example.com/photos/?gallery=Hong Kong 2008-02&photo=1",
            "http://example.com/photos/?gallery=Hong%20Kong%202008-02&photo=1",
            id="spaces-in-qs",
        ),
        pytest.param(
            "https://example.com",
            r"https://example.com\articles\1",
            "https://example.com/articles/1",
            id="backslash-instead-of-slash",
        ),
        pytest.param(
            "https://example.com",
            "https://example.com/articles/1.html",
            "https://example.com/articles/1.html",
            id="ends-with-html",
        ),
        pytest.param(
            "https://example.com/toto/article.html",
            "articles/1.svg",
            "https://example.com/articles/1.svg",
            id="no-starting-slash",
        ),
    ],
)
def test_normalize_url(base_url: str, url_to_normalize: str, expected_normalized_url: str):
    normalized_url = normalize_url(base_url, url_to_normalize)

    assert normalized_url == expected_normalized_url


@pytest.mark.parametrize(
    "url_to_normalize",
    [
        pytest.param("Trash it", id="trash"),
        pytest.param("", id="empty-url"),
    ],
)
def test_normalize_invalid_url(url_to_normalize: str):
    with pytest.raises(ValueError, match=f"Failed to normalize URL: {url_to_normalize}"):
        normalize_url("https://example.com", url_to_normalize)
