# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from collections.abc import Mapping
from json import JSONDecodeError
from typing import Any

from django.forms import widgets


class SelectMultipleAutocompleteWidget(widgets.SelectMultiple):
    template_name = "core/widgets/select_multiple_autocomplete.html"

    def __init__(self, attrs=None, choices=(), *, allow_new: bool = True, empty_label=""):
        attrs = attrs or {}
        attrs["data-bs5-tags"] = "true"
        if allow_new:
            attrs["data-allow-new"] = "true"
        super().__init__(attrs, choices)
        self._empty_label = empty_label

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"]["empty_label"] = self._empty_label
        return ctx

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        classes = attrs.get("class", "")
        classes = f"{classes} visually-hidden"
        attrs["class"] = classes
        return attrs


class SelectAutocompleteWidget(widgets.Select):
    template_name = "core/widgets/select_autocomplete.html"

    def __init__(self, attrs=None, choices=(), *, allow_new: bool = True):
        attrs = attrs or {}
        attrs["data-bs5-tags"] = "true"
        if allow_new:
            attrs["data-allow-new"] = "true"
        super().__init__(attrs, choices)

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        classes = attrs.get("class", "")
        classes = f"{classes} visually-hidden"
        attrs["class"] = classes
        return attrs


class PrettyJSONWidget(widgets.Textarea):
    """Pretty format JSON data in a textarea.

    From https://stackoverflow.com/a/52627264
    """

    def format_value(self, value):
        try:
            value = json.dumps(json.loads(value), indent=2, sort_keys=True)
            # these lines will try to adjust size of TextArea to fit to content
            row_lengths = [len(r) for r in value.split("\n")]
            self.attrs["rows"] = min(max(len(row_lengths) + 2, 10), 30)
            self.attrs["cols"] = min(max(max(row_lengths) + 2, 40), 120)
            return value
        except JSONDecodeError, ValueError, TypeError:
            return super().format_value(value)


class DateTimeWidget(widgets.DateTimeInput):
    input_type = "datetime-local"


class ListWidget(widgets.Widget):
    def value_from_datadict(self, data: Mapping[str, Any], files: Any, name: str):
        if not hasattr(data, "getlist"):
            return []
        return data.getlist(name, [])
