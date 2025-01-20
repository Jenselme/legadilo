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
