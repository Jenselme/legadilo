#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import BaseCommand

from legadilo.users.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Display some stats about active users and created accounts"

    def handle(self, *args, **options):
        data = User.objects.compute_stats()

        stats = ""
        for key, value in data.items():
            stats += f"{key}: {value}\n"

        logger.info(stats)

        admin_emails = User.objects.list_admin_emails()
        send_mail(
            subject="[Legadilo] User stats",
            message=stats,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
        )
        logger.info("Data sent to administrators by email")
