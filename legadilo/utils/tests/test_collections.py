import pytest

from legadilo.utils.collections import max_or_none, min_or_none
from legadilo.utils.time import utcdt


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
