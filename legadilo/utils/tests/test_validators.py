import pytest
from django.core.exceptions import ValidationError

from ..validators import (
    get_page_number_from_request,
    is_url_valid,
    list_of_strings_json_schema_validator,
    normalize_url,
)


class TestListOfStringsJsonSchemaValidator:
    def test_list_of_string_json_schema_validator_with_array_of_strings(self):
        # Must not raise.
        list_of_strings_json_schema_validator(["Value1", "2", "Hi!"])

    @pytest.mark.parametrize(
        "value",
        [
            ["Test", 1],
            {"nota": "a list"},
            "Just a string",
        ],
    )
    def test_list_of_string_json_schema_validator_with_invalid_data(self, value):
        with pytest.raises(ValidationError):
            list_of_strings_json_schema_validator(value)


@pytest.mark.parametrize(
    ("request_params", "expected_value"),
    [
        ({}, 1),
        ({"page": "1"}, 1),
        ({"page": "4"}, 4),
        ({"page": "aaa"}, 1),
    ],
)
def test_get_page_number(rf, request_params, expected_value):
    request = rf.get("/", request_params)

    assert get_page_number_from_request(request) == expected_value


@pytest.mark.parametrize(
    ("sample_url", "expected_is_valid"),
    [
        pytest.param("//jujens.eu/toto", True, id="url-no-scheme"),
        pytest.param("https://jujens.eu/toto", True, id="url-with-scheme"),
        pytest.param("jujens.eu/toto", False, id="url-no-scheme-no-double-slash"),
        pytest.param("/toto", False, id="path-only"),
        pytest.param("Hello world!", False, id="trash"),
    ],
)
def test_is_url_valid(sample_url: str, expected_is_valid: bool):
    is_valid = is_url_valid(sample_url)

    assert is_valid == expected_is_valid


@pytest.mark.parametrize(
    ("url_to_normalize", "expected_normalized_url"),
    [
        pytest.param("https://example.com/toto", "https://example.com/toto", id="already-full-url"),
        pytest.param("//example.com/toto", "https://example.com/toto", id="url-without-scheme"),
        pytest.param(
            "example.com/toto", "https://example.com/toto", id="no-scheme-nor-double-slash"
        ),
        pytest.param("/toto", "https://example.com/toto", id="path-only"),
    ],
)
def test_normalize_url(url_to_normalize: str, expected_normalized_url: str):
    normalized_url = normalize_url("https://example.com", url_to_normalize)

    assert normalized_url == expected_normalized_url


@pytest.mark.parametrize(
    "url_to_normalize",
    [
        pytest.param("Trash it", id="trash"),
        pytest.param("", id="empty-url"),
    ],
)
def test_normalize_invalid_url(url_to_normalize: str):
    with pytest.raises(ValueError, match=f"Failed to normalize URL: {url_to_normalize}"):
        normalize_url("https://example.com", url_to_normalize)
