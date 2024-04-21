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
