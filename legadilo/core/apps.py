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

from django.apps import AppConfig
from django.core import checks


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legadilo.core"

    def ready(self) -> None:
        from .checks import check_dev_mode, check_model_names  # noqa: PLC0415

        checks.register(check_model_names)
        checks.register(check_dev_mode)
