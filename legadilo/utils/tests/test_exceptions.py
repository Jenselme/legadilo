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

from ssl import SSLCertVerificationError

import httpx
import pytest

from legadilo.utils.exceptions import extract_debug_information, format_exception


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
