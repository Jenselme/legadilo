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

from typing import Any

from asgiref.sync import async_to_sync
from django.core.management import BaseCommand


class AsyncCommand(BaseCommand):
    async def run(self, *args: Any, **options: Any) -> str | None:
        raise NotImplementedError

    def handle(self, *args: Any, **options: Any) -> str | None:
        return async_to_sync(self.run)(*args, **options)
