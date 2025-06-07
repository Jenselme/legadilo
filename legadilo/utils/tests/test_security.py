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

from legadilo.utils.security import full_sanitize, sanitize_keep_safe_tags


@pytest.mark.parametrize(
    ("data", "clean_data"),
    [
        pytest.param("", "", id="empty-string"),
        pytest.param("<p>Test</p>", "Test", id="basic-html"),
        pytest.param("<div>Test <p>complete</p></div>", "Test complete", id="nested-html"),
        pytest.param("<div>Hello", "Hello", id="invalid-html"),
    ],
)
def test_full_sanitize(data, clean_data):
    cleaned_data = full_sanitize(data)

    assert cleaned_data == clean_data


@pytest.mark.parametrize(
    ("data", "clean_data"),
    [
        pytest.param("", "", id="empty-string"),
        pytest.param("<p>Test</p>", "<p>Test</p>", id="basic-html"),
        pytest.param(
            "<div>Test <p>complete</p></div>", "<div>Test <p>complete</p></div>", id="nested-html"
        ),
        pytest.param("<div>Hello", "<div>Hello</div>", id="invalid-html"),
        pytest.param(
            "<script>alert('hell')</script><p>Coucou</p>", "<p>Coucou</p>", id="with-script"
        ),
        pytest.param(
            """<p><img src="/img" alt="My image" height="900">Test</p>""",
            """<p><img src="/img" alt="My image">Test</p>""",
            id="image",
        ),
        pytest.param(
            """<p id="my-id" class="some-class" data-stuff="test">Test</p>""",
            """<p id="my-id">Test</p>""",
            id="with-attributes",
        ),
    ],
)
def test_sanitize_keep_safe_tags(data: str, clean_data: str):
    cleaned_data = sanitize_keep_safe_tags(data)

    assert cleaned_data == clean_data


def test_sanitize_keep_safe_tags_empty_with_extra_cleanup():
    cleaned_data = sanitize_keep_safe_tags(
        """<p>Hello world to <a href="/toto">you</a&""", extra_tags_to_cleanup={"a"}
    )

    assert cleaned_data == """<p>Hello world to you</p>"""
