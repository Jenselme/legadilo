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
