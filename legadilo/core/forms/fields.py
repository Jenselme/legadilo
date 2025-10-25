# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from .widgets import ListWidget, SelectMultipleAutocompleteWidget


class MultipleTagsField(forms.MultipleChoiceField):
    widget = SelectMultipleAutocompleteWidget(empty_label=_("Choose tags"))

    def validate(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages["required"], code="required")

        if not all(value):
            raise ValidationError(_("Tag cannot be empty."), code="empty-tag")

        if not all(slugify(tag_value) for tag_value in value):
            raise ValidationError(
                _("Tag cannot contain only spaces or special characters."),
                code="tag-cannot-be-slugified",
            )


class SlugifiableCharField(forms.CharField):
    def validate(self, value):
        if not slugify(value):
            raise ValidationError(
                _("Cannot contain only spaces or special characters."),
                code="cannot-be-slugified",
            )


class ListField(forms.Field):
    field: forms.Field
    widget = ListWidget

    def __init__(self, *args, field: forms.Field, **kwargs):
        self.field = field
        super().__init__(*args, **kwargs)

    def validate(self, value: list[str]):
        for v in value:
            self.field.validate(v)

    def clean(self, value: list[str]):
        return [self.field.clean(v) for v in value]
