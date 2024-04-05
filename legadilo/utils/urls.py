from django.db.models import TextChoices


def create_path_converter_from_enum(enum_type: type[TextChoices]) -> type:
    names = "|".join(enum_type.names)

    class FromEnumPathConverter:
        regex = rf"({names})"

        def to_python(self, value: str) -> TextChoices:
            return enum_type(value)

        def to_url(self, value: TextChoices) -> str:
            return str(value)

    return FromEnumPathConverter
