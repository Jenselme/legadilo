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

import pytest

from legadilo.utils.text import get_nb_words_from_html


@pytest.mark.parametrize(
    ("input_text", "expected_nb_words"),
    [
        pytest.param("Hello world!", 2, id="no-html"),
        pytest.param("re-add", 1, id="with-dash"),
        pytest.param("""<p class="text">Hello world!</p>""", 2, id="html"),
        pytest.param(
            """<p class="text">Hello world for 33 years!</p>""", 5, id="html-with-numbers"
        ),
        # We probably want to remove emoji. The regexp is a bit complex and I don't want a package
        # to do it. Let's live with it for now.
        pytest.param(
            """<p class="text">Hello world 😀</p>""",
            3,
            id="html-with-emojis",
        ),
    ],
)
def test_get_nb_words_from_html(input_text: str, expected_nb_words: int):
    nb_words = get_nb_words_from_html(input_text)

    assert nb_words == expected_nb_words
