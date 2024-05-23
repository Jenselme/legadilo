from django.forms import widgets


class MultipleTagsWidget(widgets.SelectMultiple):
    template_name = "core/widgets/select_tags.html"

    def __init__(self, attrs=None, choices=(), *, allow_new: bool = True):
        attrs = attrs or {}
        attrs["allow_new"] = allow_new
        super().__init__(attrs, choices)
