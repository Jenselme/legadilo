# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
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

from typing import Any

from django.db import models
from django.db.models import Model
from ninja import Schema


class ApiError(Schema):
    detail: str


async def update_model_from_patch_dict(
    model: Model,
    data: dict[str, Any],
    *,
    must_refresh: bool = False,
    refresh_qs: models.QuerySet | None = None,
):
    for attr, value in data.items():
        setattr(model, attr, value)

    await model.asave(update_fields=list(data.keys()))

    if must_refresh:
        await model.arefresh_from_db(from_queryset=refresh_qs)
