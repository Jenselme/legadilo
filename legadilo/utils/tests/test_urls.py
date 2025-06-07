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
from django.test import RequestFactory

from legadilo.utils.urls import (
    add_query_params,
    pop_query_param,
    validate_from_url,
    validate_referer_url,
)

absolute_urls_params = [
    ("http://testserver", "http://testserver/fallback", "http://testserver"),
    ("http://testserver/", "http://testserver/fallback", "http://testserver/"),
    ("http://testserver/test", "http://testserver/fallback", "http://testserver/test"),
    (
        "http://testserver/?param=value#hash",
        "http://testserver/fallback",
        "http://testserver/?param=value#hash",
    ),
    (
        "http://testserver/path/sub/?param=value#hash",
        "http://testserver/fallback",
        "http://testserver/path/sub/?param=value#hash",
    ),
    (
        "http://example.com",
        "http://testserver/fallback",
        "http://testserver/fallback",
    ),
    (
        "http://example.com/test",
        "http://testserver/fallback",
        "http://testserver/fallback",
    ),
    (
        "http://example.com/test/?param=value#hash",
        "http://testserver/fallback",
        "http://testserver/fallback",
    ),
]

relative_urls_params = [
    ("/", "/fallback", "/"),
    ("/test", "/fallback", "/test"),
    (
        "/?param=value#hash",
        "/fallback",
        "/?param=value#hash",
    ),
    (
        "/path/sub/?param=value#hash",
        "/fallback",
        "/path/sub/?param=value#hash",
    ),
]


@pytest.mark.parametrize(
    ("referer_url", "fallback_url", "expected_url"),
    absolute_urls_params,
)
def test_redirect_to_origin(referer_url, fallback_url, expected_url):
    factory = RequestFactory()
    request = factory.get("/", HTTP_REFERER=referer_url)

    validated_url = validate_referer_url(request, fallback_url)

    assert validated_url == expected_url


@pytest.mark.parametrize(
    ("from_url", "fallback_url", "expected_url"),
    [
        *absolute_urls_params,
        *relative_urls_params,
    ],
)
def test_validate_from_url(from_url, fallback_url, expected_url):
    factory = RequestFactory()
    request = factory.get("/")

    validated_url = validate_from_url(request, from_url, fallback_url)

    assert validated_url == expected_url


@pytest.mark.parametrize(
    ("url", "expected_url"),
    [
        pytest.param(
            "https://example.com", "https://example.com?my-param=my-value", id="scheme-domain"
        ),
        pytest.param("example.com", "example.com?my-param=my-value", id="domain-only"),
        pytest.param("/path", "/path?my-param=my-value", id="path-only"),
        pytest.param(
            "https://example.com/test",
            "https://example.com/test?my-param=my-value",
            id="domain-and-path",
        ),
        pytest.param(
            "https://example.com/test?my-param=wrong-value",
            "https://example.com/test?my-param=my-value",
            id="override-param",
        ),
        pytest.param(
            "https://example.com/test?some-param=some-value",
            "https://example.com/test?some-param=some-value&my-param=my-value",
            id="other-param",
        ),
    ],
)
def test_add_query_params(url: str, expected_url: str):
    built_url = add_query_params(url, {"my-param": ["my-value"]})

    assert built_url == expected_url


def test_add_empty_values_to_query_params():
    built_url = add_query_params(
        "https://example.com/test?some-param=some-value&my-other-param=value",
        {"my-param": [], "my-other-param": [None], "another-param": None, "raw-string": "my-str"},
    )

    assert built_url == "https://example.com/test?some-param=some-value&raw-string=my-str"


@pytest.mark.parametrize(
    ("url", "expected_url"),
    [
        pytest.param(
            "https://example.com?my-param=my-value", "https://example.com", id="scheme-domain"
        ),
        pytest.param("example.com?my-param=my-value", "example.com", id="domain-only"),
        pytest.param("/path?my-param=my-value", "/path", id="path-only"),
        pytest.param(
            "https://example.com/test?my-param=my-value",
            "https://example.com/test",
            id="domain-and-path",
        ),
        pytest.param(
            "https://example.com/test?some-param=some-value&my-param=my-value",
            "https://example.com/test?some-param=some-value",
            id="other-param",
        ),
    ],
)
def test_pop_query_param(url: str, expected_url: str):
    built_url = pop_query_param(url, "my-param")

    assert built_url == (expected_url, "my-value")


def test_pop_query_param_missing_param():
    built_url = pop_query_param("https://example.com/test", "my-param")

    assert built_url == ("https://example.com/test", None)
