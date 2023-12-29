import json

from django import forms
from django.utils.translation import gettext_lazy as _


class CreateFeedForm(forms.Form):
    url = forms.URLField(
        assume_scheme="https",
        help_text=_(
            "Enter the URL to the feed you want to subscribe to or of a site in which case we will "
            "try to find the URL of the feed."
        ),
    )
    feed_choices = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.HiddenInput(),
    )
    proposed_feed_choices = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        if data and (proposed_feed_choices := data.get("proposed_feed_choices")):
            self.fields["url"].widget.attrs["readonly"] = "true"
            self.initial["proposed_feed_choices"] = proposed_feed_choices
            self.fields["feed_choices"].widget = forms.RadioSelect()
            self.fields["feed_choices"].choices = self._load_proposed_feed_choices(proposed_feed_choices)
            self.fields["feed_choices"].required = True

    def _load_proposed_feed_choices(self, raw_choices):
        try:
            choices = json.loads(raw_choices)
        except json.JSONDecodeError:
            return []

        if not isinstance(choices, list):
            return []
        for value in choices:
            if len(value) != 2 or not isinstance(value[0], str) or not isinstance(value[1], str):  # noqa: PLR2004
                return []

        return choices

    class Meta:
        fields = ("url",)

    @property
    def feed_url(self):
        return self.cleaned_data.get("feed_choices") or self.cleaned_data["url"]
