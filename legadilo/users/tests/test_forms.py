# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Module for all Form Tests."""

from django.utils.translation import gettext_lazy as _

from legadilo.users.forms import UserAdminCreationForm
from legadilo.users.models import User


class TestUserAdminCreationForm:
    """Test class for all tests related to the UserAdminCreationForm."""

    def test_username_validation_error_msg(self, user: User):
        """Tests UserAdminCreation Form's unique validator functions correctly by testing:

        #. A new user with an existing username cannot be added.
        #. Only 1 error is raised by the UserCreation Form
        #. The desired error message is raised
        """
        # The user already exists,
        # hence cannot be created.
        form = UserAdminCreationForm(
            {
                "email": user.email,
                "password1": user.password,
                "password2": user.password,
            },
        )

        assert not form.is_valid()
        assert len(form.errors) == 1
        assert "email" in form.errors
        assert form.errors["email"][0] == _("This email has already been taken.")
