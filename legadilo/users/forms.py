# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.forms import EmailField, ModelChoiceField, ModelForm
from django.utils.translation import gettext_lazy as _

from legadilo.core.forms.widgets import SelectAutocompleteWidget
from legadilo.core.models import Timezone
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
        required=True,
        widget=SelectAutocompleteWidget(allow_new=False),
        help_text=_("Used to display times and updated feeds at a convenient time."),
    )

    class Meta:
        model = UserSettings
        fields = ("default_reading_time", "timezone")
