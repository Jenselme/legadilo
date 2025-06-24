# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.management import BaseCommand, CommandError, CommandParser
from django.template.loader import render_to_string

from legadilo.import_export.services.export import build_feeds_export_context, export_articles
from legadilo.users.models import User
from legadilo.utils.file import file_or_stdout


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "--user-id",
            "-u",
            dest="user_id",
            type=int,
            required=True,
            help="For which user to export the data",
        )
        parser.add_argument(
            "--output",
            "-o",
            dest="output",
            type=str,
            default=None,
            help="Output file. Data will be printed to stdout if not set.",
        )
        parser.add_argument(
            "export_type",
            choices=["feeds", "articles"],
            help="Type of data to export",
            nargs=1,
        )

    def handle(self, *args, **options):
        user = User.objects.get(id=options["user_id"])

        with file_or_stdout(options["output"]) as output:
            match options["export_type"][0]:
                case "feeds":
                    context = build_feeds_export_context(user)
                    output.write(render_to_string("import_export/export_feeds.opml", context))
                case "articles":
                    for data in export_articles(user):
                        output.write(data)
                case _:
                    raise CommandError("Unknown export type")
