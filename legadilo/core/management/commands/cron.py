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
