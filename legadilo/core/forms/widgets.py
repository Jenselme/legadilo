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

import json
from json import JSONDecodeError

from django.forms import widgets


class MultipleTagsWidget(widgets.SelectMultiple):
    template_name = "core/widgets/select_tags.html"

    def __init__(self, attrs=None, choices=(), *, allow_new: bool = True):
        attrs = attrs or {}
        attrs["data-bs5-tags"] = "true"
        if allow_new:
            attrs["data-allow-new"] = "true"
        super().__init__(attrs, choices)


class AutocompleteSelectWidget(widgets.Select):
    template_name = "core/widgets/select_autocomplete.html"

    def __init__(self, attrs=None, choices=(), *, allow_new: bool = True):
        attrs = attrs or {}
        attrs["data-bs5-tags"] = "true"
        if allow_new:
            attrs["data-allow-new"] = "true"
        super().__init__(attrs, choices)


class PrettyJSONWidget(widgets.Textarea):
    """From https://stackoverflow.com/a/52627264"""

    def format_value(self, value):
        try:
            value = json.dumps(json.loads(value), indent=2, sort_keys=True)
            # these lines will try to adjust size of TextArea to fit to content
            row_lengths = [len(r) for r in value.split("\n")]
            self.attrs["rows"] = min(max(len(row_lengths) + 2, 10), 30)
            self.attrs["cols"] = min(max(max(row_lengths) + 2, 40), 120)
            return value
        except (JSONDecodeError, ValueError, TypeError):
            return super().format_value(value)


class DateTimeWidget(widgets.DateTimeInput):
    input_type = "datetime-local"
