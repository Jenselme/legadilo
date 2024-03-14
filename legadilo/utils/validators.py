from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema


@deconstructible
class JsonSchemaValidator:
    def __init__(self, schema):
        self._schema = schema

    def __call__(self, value):
        try:
            validate_json_schema(value, self._schema)
        except JsonSchemaValidationError as e:
            raise ValidationError(str(e)) from e


list_of_strings_json_schema_validator = JsonSchemaValidator({
    "type": "array",
    "items": {"type": "string"},
})
