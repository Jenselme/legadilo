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

from legadilo.utils.collections_utils import max_or_none, merge_deletion_results, min_or_none
from legadilo.utils.time_utils import utcdt


@pytest.mark.parametrize(
    ("collection", "expected"),
    [
        pytest.param([], None, id="empty"),
        pytest.param([1], 1, id="one-item"),
        pytest.param([3, 1, 2], 1, id="list-of-items"),
        pytest.param([None, 3, None], 3, id="with-holes"),
        pytest.param(
            [utcdt(2024, 3, 1), utcdt(2024, 5, 1), utcdt(2024, 4, 1)],
            utcdt(2024, 3, 1),
            id="other-types",
        ),
    ],
)
def test_min_or_none(collection, expected):
    item = min_or_none(collection)

    assert item == expected


@pytest.mark.parametrize(
    ("collection", "expected"),
    [
        pytest.param([], None, id="empty"),
        pytest.param([1], 1, id="one-item"),
        pytest.param([1, 3, 2], 3, id="list-of-items"),
        pytest.param([None, 3, None], 3, id="with-holes"),
        pytest.param(
            [utcdt(2024, 3, 1), utcdt(2024, 5, 1), utcdt(2024, 4, 1)],
            utcdt(2024, 5, 1),
            id="other-types",
        ),
    ],
)
def test_max_or_none(collection, expected):
    item = max_or_none(collection)

    assert item == expected


@pytest.mark.parametrize(
    ("deletion_results", "expected"),
    [
        pytest.param([], (0, {}), id="empty"),
        pytest.param([(1, {"a": 1})], (1, {"a": 1}), id="one-item"),
        pytest.param(
            [(1, {"a": 1}), (2, {"b": 2}), (3, {"a": 1, "b": 2})],
            (6, {"a": 2, "b": 4}),
            id="list-of-items",
        ),
    ],
)
def test_merge_deletion_results(deletion_results, expected):
    assert merge_deletion_results(deletion_results) == expected
