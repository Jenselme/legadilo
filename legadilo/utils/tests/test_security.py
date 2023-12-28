import pytest

from legadilo.utils.security import full_sanitize


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
