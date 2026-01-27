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
        "Remove users who did not log in for more than 2 years. "
        "Email inactive users who have not logged in for a long time before deletion to allow "
        "them to log in and export their data if needed. "
        "Clear expired sessions. "
    )

    def handle(self, *args, **options):
        nb_notified_users = User.objects.notify_inactive_accounts()
        logger.info("Notified %s inactive users.", nb_notified_users)
        deletion_result = User.objects.cleanup_inactive_users()
        logger.info("Removed %s inactive accounts.", deletion_result)
        deletion_result = User.objects.cleanup_invalid_accounts()
        logger.info("Removed %s invalid accounts.", deletion_result)
        SessionStore.clear_expired()
        logger.info("Cleared expired sessions.")
