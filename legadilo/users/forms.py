# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from allauth.account.forms import LoginForm, SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.forms import ChoiceField, EmailField, ModelChoiceField, ModelForm
from django.utils.translation import gettext_lazy as _

from legadilo.core.forms.widgets import SelectAutocompleteWidget
from legadilo.core.models import Timezone
from legadilo.core.utils.locale import enforce_language_on_response
from legadilo.users import constants
from legadilo.users.models import UserSettings

User = get_user_model()


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """Form for User Creation in the Admin Area.

    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        fields = ("email",)
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


class UserLoginForm(LoginForm):
    def login(self, request, *args, **kwargs):
        response = super().login(request, *args, **kwargs)
        enforce_language_on_response(response, request.user.settings.language)
        return response


class UserSignupForm(SignupForm):
    """Form that will be rendered on a user sign up section/screen.

    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """

    timezone = ModelChoiceField(
        Timezone.objects.all(),
        required=True,
        widget=SelectAutocompleteWidget(allow_new=False),
        help_text=_("Used to display times and updated feeds at a convenient time."),
    )
    language = ChoiceField(
        label=_("Language"),
        required=False,
        choices=constants.LANGUAGE_CHOICES,
        help_text=_(
            "Set this to force the language of the app. "
            "By default, it will use your browser language. If the "
            "language is not supported, it will fallback to English. "
            "This will also enable you to receive emails in this language."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["timezone"] = Timezone.objects.get_default()


class UserSocialSignupForm(SocialSignupForm):
    """Renders the form when user has signed up using social accounts.

    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


class UserSettingsForm(ModelForm):
    timezone = ModelChoiceField(
        Timezone.objects.all(),
        label=_("Timezone"),
        required=True,
        widget=SelectAutocompleteWidget(allow_new=False),
        help_text=_("Used to display times and updated feeds at a convenient time."),
    )

    class Meta:
        model = UserSettings
        fields = ("default_reading_time", "timezone", "language")
        labels = {"default_reading_time": _("Default reading time"), "language": _("Language")}
        help_texts = {
            "language": _(
                "Set this to force the language of the app. "
                "By default, it will use your browser language. If the "
                "language is not supported, it will fallback to English. "
                "This will also enable you to receive emails in this language."
            )
        }
