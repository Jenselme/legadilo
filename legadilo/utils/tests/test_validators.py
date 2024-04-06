import pytest
from django.core.exceptions import ValidationError

from ..validators import get_page_number_from_request, list_of_strings_json_schema_validator


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
