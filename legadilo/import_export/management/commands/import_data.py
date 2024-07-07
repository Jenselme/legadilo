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

import logging
from json import JSONDecodeError
from xml.etree.ElementTree import (  # noqa: S405 etree methods are vulnerable to XML attacks
    ParseError as XmlParseError,
)

from django.core.management import BaseCommand
from django.core.management.base import CommandError, CommandParser
from django.db import transaction
from jsonschema import ValidationError as JsonSchemaValidationError

from legadilo.import_export.services.custom_csv import import_custom_csv_file_sync
from legadilo.import_export.services.exceptions import DataImportError
from legadilo.import_export.services.opml import import_opml_file_sync
from legadilo.import_export.services.wallabag import import_wallabag_json_file_path
from legadilo.users.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Import any data format we support and files of any files.

    Can be used to import feeds, categories and articles.
    """

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "--source-type",
            "-s",
            dest="source_type",
            required=True,
            type=str,
            choices=["wallabag", "opml", "custom_csv"],
            help="What is the source type you are trying to import",
        )
        parser.add_argument(
            "--user-id",
            "-u",
            dest="user_id",
            required=True,
            type=int,
            help="For which user to link the imported data",
        )
        parser.add_argument(
            "file_to_import",
            help="Path to the file to import",
            nargs=1,
        )

    def handle(self, *args, **options):
        logger.info(
            f"Starting import of {options["file_to_import"][0]} with type {options["source_type"]}"
        )
        try:
            self._import(options)
        except User.DoesNotExist as e:
            raise CommandError(f"No user with id {options["user_id"]} was found!") from e
        except JsonSchemaValidationError as e:
            logger.debug(str(e))
            raise CommandError("The file you supplied is not valid") from e
        except FileNotFoundError as e:
            raise CommandError(f"{options["file_to_import"][0]} does not exist") from e
        except JSONDecodeError as e:
            raise CommandError(f"{options["file_to_import"][0]} is not a valid JSON") from e
        except XmlParseError as e:
            raise CommandError(f"{options["file_to_import"][0]} is not a valid OPML") from e
        except DataImportError as e:
            logger.exception("Failed to import data")
            raise CommandError("Failed to import data.") from e

    @transaction.atomic()
    def _import(self, options):
        user = User.objects.get(id=options["user_id"])
        match options["source_type"]:
            case "wallabag":
                nb_imported_articles = import_wallabag_json_file_path(
                    user, options["file_to_import"][0]
                )
                logger.info(f"Imported {nb_imported_articles} articles")
            case "opml":
                nb_imported_feeds, nb_imported_categories = import_opml_file_sync(
                    user, options["file_to_import"][0]
                )
                logger.info(
                    f"Imported {nb_imported_feeds} feeds in {nb_imported_categories} feed "
                    f"categories"
                )
            case "custom_csv":
                nb_imported_articles, nb_imported_feeds, nb_imported_categories = (
                    import_custom_csv_file_sync(user, options["file_to_import"][0])
                )
                logger.info(
                    f"Imported {nb_imported_articles} articles, {nb_imported_feeds} feeds "
                    f"and {nb_imported_categories} feed categories"
                )
            case _:
                raise CommandError("Unknown source type")
