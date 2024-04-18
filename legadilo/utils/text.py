import string

from legadilo.utils.security import full_sanitize


def get_nb_words_from_html(text: str) -> int:
    raw_content = full_sanitize(text)
    nb_words = 0
    for word in raw_content.split():
        if word.strip(string.punctuation):
            nb_words += 1

    return nb_words
