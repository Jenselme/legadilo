import json
from json import JSONDecodeError

from django.forms import widgets


class MultipleTagsWidget(widgets.SelectMultiple):
    template_name = "core/widgets/select_tags.html"

    def __init__(self, attrs=None, choices=(), *, allow_new: bool = True):
        attrs = attrs or {}
        attrs["allow_new"] = allow_new
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
