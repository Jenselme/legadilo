import logging
from json import JSONDecodeError
from xml.etree.ElementTree import (  # noqa: S405 etree methods are vulnerable to XML attacks
    ParseError as XmlParseError,
)

from django.core.management import BaseCommand
from django.core.management.base import CommandError, CommandParser
from django.db import transaction
from jsonschema import ValidationError as JsonSchemaValidationError

from legadilo.import_export.services.exceptions import DataImportError
from legadilo.import_export.services.opml import import_opml_file
from legadilo.import_export.services.wallabag import import_wallabag_json_file
from legadilo.users.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "--source-type",
            "-s",
            dest="source_type",
            required=True,
            type=str,
            choices=["wallabag", "opml"],
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
                nb_imported_articles = import_wallabag_json_file(user, options["file_to_import"][0])
                logger.info(f"Imported {nb_imported_articles} articles")
            case "opml":
                nb_imported_feeds, nb_imported_categories = import_opml_file(
                    user, options["file_to_import"][0]
                )
                logger.info(
                    f"Imported {nb_imported_feeds} feeds in {nb_imported_categories} categories"
                )
            case _:
                raise CommandError("Unknown source type")