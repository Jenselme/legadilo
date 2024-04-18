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
