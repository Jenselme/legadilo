# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from legadilo.utils.text import ClearableStringIO, get_nb_words_from_html


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


class TestClearableStringIO:
    def test_multiple_get_value(self):
        buffer = ClearableStringIO()

        buffer.write("Line 1\n")
        buffer.write("Line 2\n")
        assert buffer.getvalue() == "Line 1\nLine 2\n"

        buffer.write("Line 3\n")
        buffer.clear()
        assert not buffer.getvalue()

        buffer.write("Line 4\n")
        assert buffer.getvalue() == "Line 4\n"
