from django.conf import settings


def get_article_fixture_content(name: str):
    file_path = settings.APPS_DIR / "reading/tests/fixtures/articles" / name
    with file_path.open() as f:
        return f.read()
