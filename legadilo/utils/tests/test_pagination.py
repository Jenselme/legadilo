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
