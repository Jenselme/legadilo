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

from pathlib import Path
from pprint import pprint

from django.core.management import CommandError
from django.core.management.base import CommandParser

from legadilo.feeds.services.feed_parsing import build_feed_data_from_parsed_feed, parse_feed
from legadilo.utils.command import AsyncCommand
from legadilo.utils.http import get_rss_async_client
from legadilo.utils.validators import is_url_valid


class Command(AsyncCommand):
    """Read a feed and prints some data about it.

    It's only useful for quickly debugging a feed or checking CPU and memory usage on big feed
    files.
    """

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "feed_file",
            help="The feed file to read (file on disk or HTTP link).",
            nargs=1,
        )
        parser.add_argument(
            "--print", help="Print the parsed data", default=False, action="store_true"
        )

    async def run(self, *args, **options):
        file_content = await self._read_feed(options["feed_file"][0])
        parsed_feed = parse_feed(file_content, resolve_relative_uris=True, sanitize_html=False)
        feed_data = build_feed_data_from_parsed_feed(parsed_feed, options["feed_file"][0])

        print(  # noqa: T201 print found
            f"Feed {feed_data.title} ({feed_data.feed_type}) about {feed_data.description} "
            f"from {feed_data.site_url} has {len(feed_data.articles)} articles"
        )
        if options["print"]:
            pprint(feed_data)  # noqa: T203 pprint found

    async def _read_feed(self, feed_file):
        file_path = Path(feed_file)
        if file_path.exists() and file_path.is_file():
            with file_path.open("r", encoding="utf-8") as f:  # noqa: ASYNC230 async functions calling open
                return f.read()

        if is_url_valid(feed_file):
            async with get_rss_async_client() as client:
                response = await client.get(feed_file)
                return response.raise_for_status().text

        raise CommandError(f"Failed to find file {feed_file}")
