# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from legadilo.core.utils.collections_utils import max_or_none, merge_deletion_results, min_or_none
from legadilo.core.utils.time_utils import utcdt


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
