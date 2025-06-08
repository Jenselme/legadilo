# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from .widgets import SelectMultipleAutocompleteWidget


class MultipleTagsField(forms.MultipleChoiceField):
    widget = SelectMultipleAutocompleteWidget(empty_label=_("Choose tags"))

    def validate(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages["required"], code="required")

        if not all(value):
            raise ValidationError(_("Tag cannot be empty"), code="empty-tag")

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
