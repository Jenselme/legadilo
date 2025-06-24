# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from legadilo.reading.models import Article


def delete_article(article: Article):
    """Delete article even if linked to a feed.

    Rely on FeedDeletedArticle to do this properly. This is an acceptable exceptoin to our
    boundary policy since it's isolated from the rest and very limited.
    """
    from legadilo.feeds.models import (  # noqa: PLC0415 `import` should be at the top-level of a file
        FeedDeletedArticle,
    )

    FeedDeletedArticle.objects.delete_article(article)
