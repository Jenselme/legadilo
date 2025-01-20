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

import sys

from django.apps import apps
from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning as CheckWarning

SAFE_MODEL_NAMES: set[str] = {"UserSettings"}


def check_model_names(*, app_configs, **kwargs):
    if app_configs is None:
        app_configs = apps.get_app_configs()

    errors = []
    for app_config in app_configs:
        # Skip apps that aren't part of the project
        if not app_config.name.startswith("legadilo."):
            continue
        for model in app_config.get_models():
            class_name = model.__name__
            if class_name.endswith("s") and class_name not in SAFE_MODEL_NAMES:
                error = Error(
                    "Model names should be singular.",
                    hint=(
                        "Rename to the singular form, e.g. "
                        f"“{class_name.removesuffix('s')}”, or mark the "
                        f"name as allowed by adding {class_name!r} to "
                        f"{__name__}.SAFE_MODEL_NAMES."
                    ),
                    obj=model,
                    id="legadilo.E001",
                )
                errors.append(error)

    return errors


def check_dev_mode(**kwargs):
    errors = []
    if settings.DEBUG and not sys.flags.dev_mode:
        errors.append(
            CheckWarning(
                "Python development mode is not active with DEBUG.",
                hint="Set the environment variable PYTHONDEVMODE=1, or run with 'python -X dev'.",
                id="legadilo.W001",
            )
        )

    return errors
