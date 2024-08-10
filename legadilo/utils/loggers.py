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

logger = logging.getLogger(__name__)


def unlink_logger_from_sentry(logger_to_ignore: logging.Logger):
    try:
        from sentry_sdk.integrations.logging import (  # noqa: PLC0415 `import` should be at the top-level of a file
            ignore_logger,
        )
    except ImportError:
        logger.debug("Sentry is not installed. No need to ignore it.")
    else:
        ignore_logger(logger_to_ignore.name)
