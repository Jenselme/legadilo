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

import string
from io import StringIO

from legadilo.utils.security import full_sanitize


def get_nb_words_from_html(text: str) -> int:
    raw_content = full_sanitize(text)
    nb_words = 0
    for word in raw_content.split():
        if word.strip(string.punctuation):
            nb_words += 1

    return nb_words


class ClearableStringIO:
    """A buffer we can write to that resets on every read."""

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
