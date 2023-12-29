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

    class Meta:
        fields = ("url",)
