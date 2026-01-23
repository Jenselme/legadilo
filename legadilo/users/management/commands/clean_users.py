# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.core.management import BaseCommand

from legadilo.users.models import User
from legadilo.users.session_store import SessionStore

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Remove users whose account has never been created but not activated in the last 90 days. "
        "Clear expired sessions. "
    )

    def handle(self, *args, **options):
        deletion_result = User.objects.cleanup_invalid_accounts()
        logger.info("Removed %s inactive accounts.", deletion_result)
        SessionStore.clear_expired()
        logger.info("Cleared expired sessions.")
