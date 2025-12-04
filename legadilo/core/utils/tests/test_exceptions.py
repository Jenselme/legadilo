# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from ssl import SSLCertVerificationError

import httpx
import pytest

from legadilo.core.utils.exceptions import extract_debug_information, format_exception


@pytest.mark.parametrize(
    ("exception", "expected_text"),
    [
        (
            Exception(),
            "Exception",
        ),
        (RuntimeError(), "RuntimeError"),
        (IndexError("Not found"), "IndexError(Not found)"),
    ],
)
def test_format_exception(exception, expected_text):
    text = format_exception(exception)

    assert text == expected_text


@pytest.mark.parametrize(
    ("exception", "expected_data"),
    [
        pytest.param(
            SSLCertVerificationError(), {"request": None, "response": None}, id="SSLException"
        ),
        pytest.param(
            httpx.HTTPError("Oops"), {"request": None, "response": None}, id="HTTPError no request"
        ),
        pytest.param(
            httpx.HTTPStatusError(
                "Oops",
                request=httpx.Request(
                    method="GET", url="https://example.com/article", headers={"X-Debug": "True"}
                ),
                response=httpx.Response(status_code=200, headers={"Content-Type": "text"}),
            ),
            {
                "request": {
                    "headers": {"host": "example.com", "x-debug": "True"},
                    "method": "GET",
                    "url": "https://example.com/article",
                },
                "response": {
                    "headers": {"content-type": "text"},
                    "reason_phrase": "OK",
                    "status_code": 200,
                },
            },
            id="HTTPStatusError",
        ),
    ],
)
def test_extract_debug_information(exception, expected_data):
    technical_data = extract_debug_information(exception)

    assert technical_data == expected_data
