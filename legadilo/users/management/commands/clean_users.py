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

import logging

from django.core.management import BaseCommand

from legadilo.users.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Remove users whose account has never been created but not activated in the last 90 days."
    )

    def handle(self, *args, **options):
        deletion_result = User.objects.cleanup_invalid_accounts()
        logger.info("Removed %s inactive accounts.", deletion_result)
