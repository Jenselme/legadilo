# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import string
from io import StringIO

from legadilo.core.utils.security import full_sanitize


def get_nb_words_from_html(text: str) -> int:
    raw_content = full_sanitize(text)
    nb_words = 0
    for word in raw_content.split():
        if word.strip(string.punctuation):
            nb_words += 1

    return nb_words


class ClearableStringIO:
    """A buffer we can write to that resets on every read.

    Can be passed to a CSV writer to hold only the data not yet transmitted over HTTP. This way,
    the full data isn't loaded in the buffer, only the data that's not yet transmitted.
    """

    def __init__(self):
        self.buffer = StringIO()

    def write(self, value):
        self.buffer.write(value)

    def getvalue(self):
        value = self.buffer.getvalue()
        self.clear()
        return value

    def clear(self):
        self.buffer = StringIO()
