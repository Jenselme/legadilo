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

from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.forms import EmailField, ModelChoiceField, ModelForm
from django.utils.translation import gettext_lazy as _

from legadilo.core.forms.widgets import AutocompleteSelectWidget
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
        widget=AutocompleteSelectWidget(),
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
        widget=AutocompleteSelectWidget(),
        help_text=_("Used to display times and updated feeds at a convenient time."),
    )

    class Meta:
        model = UserSettings
        fields = ("default_reading_time", "timezone")
