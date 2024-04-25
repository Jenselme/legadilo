from django import forms
from django.core.exceptions import ValidationError

from .widgets import MultipleTagsWidget


class MultipleTagsField(forms.MultipleChoiceField):
    widget = MultipleTagsWidget

    def validate(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages["required"], code="required")
