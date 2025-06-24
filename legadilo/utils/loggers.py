# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

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
