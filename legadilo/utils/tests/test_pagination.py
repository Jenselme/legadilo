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

import pytest
from django.core.paginator import Paginator

from legadilo.utils.pagination import get_requested_page


@pytest.mark.parametrize(
    ("paginator", "requested_page", "expected_page"),
    [
        pytest.param(Paginator([1, 2, 3], 1), 1, 1, id="ask-first-page"),
        pytest.param(Paginator([1, 2, 3], 1), 2, 2, id="ask-existing-page"),
        pytest.param(Paginator([1, 2, 3], 1), 3, 3, id="ask-last-page"),
        pytest.param(Paginator([1, 2, 3], 1), 1, 1, id="ask-negative-page"),
        pytest.param(Paginator([1, 2, 3], 1), 10, 1, id="ask-non-existent-page"),
    ],
)
def test_get_requested_page(paginator: Paginator, requested_page: int, expected_page: int):
    page = get_requested_page(paginator, requested_page)

    assert page.number == expected_page
