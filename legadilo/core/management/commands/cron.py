# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from time import sleep

from django.core.management import BaseCommand, call_command

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Commodity command to run all scheduled tasks with one command. It will refresh feeds "
        "and clean what needs to be cleaned."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--schedule",
            nargs=1,
            type=int,
            default=[1],
            help=(
                "Frequency (in hours) at which to run the cron jobs. For all numbers equals or"
                "below 0 run the command and exit."
            ),
        )

    def handle(self, *args, **options):
        schedule = options["schedule"][0]
        logger.info(f"Starting cron running every {schedule} hour(s)")

        while True:
            logger.info("Starting commands")
            call_command("update_feeds")
            call_command("clearsessions")
            call_command("clean_data")
            call_command("clean_users")
            logger.info("Finished running commands")

            if schedule <= 0:
                break

            sleep(schedule * 3_600)
