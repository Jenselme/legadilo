from django.forms import widgets


class MultipleTagsWidget(widgets.SelectMultiple):
    template_name = "core/widgets/select_tags.html"
