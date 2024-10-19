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
from django.urls import reverse

from legadilo.reading import constants
from legadilo.reading.templatetags import (
    decode_external_tag,
    encode_external_tag,
    favorite_action_url,
    for_later_action_url,
    markdown,
    read_action_url,
)
from legadilo.reading.tests.factories import ArticleFactory


@pytest.mark.parametrize(
    ("is_read", "update_action"),
    [
        pytest.param(
            True, constants.UpdateArticleActions.MARK_AS_UNREAD.name, id="article-is-read"
        ),
        pytest.param(
            False, constants.UpdateArticleActions.MARK_AS_READ.name, id="article-is-not-read"
        ),
    ],
)
def test_read_action_url(is_read, update_action):
    article = ArticleFactory.build(id=1, is_read=is_read)

    url = read_action_url(article)

    assert url == reverse(
        "reading:update_article", kwargs={"article_id": 1, "update_action": update_action}
    )


@pytest.mark.parametrize(
    ("is_favorite", "update_action"),
    [
        pytest.param(
            True, constants.UpdateArticleActions.UNMARK_AS_FAVORITE.name, id="article-is-favorite"
        ),
        pytest.param(
            False,
            constants.UpdateArticleActions.MARK_AS_FAVORITE.name,
            id="article-is-not-favorite",
        ),
    ],
)
def test_favorite_action_url(is_favorite, update_action):
    article = ArticleFactory.build(id=1, is_favorite=is_favorite)

    url = favorite_action_url(article)

    assert url == reverse(
        "reading:update_article", kwargs={"article_id": 1, "update_action": update_action}
    )


@pytest.mark.parametrize(
    ("is_for_later", "update_action"),
    [
        pytest.param(
            True, constants.UpdateArticleActions.UNMARK_AS_FOR_LATER.name, id="article-is-favorite"
        ),
        pytest.param(
            False,
            constants.UpdateArticleActions.MARK_AS_FOR_LATER.name,
            id="article-is-not-favorite",
        ),
    ],
)
def test_for_later_action_url(is_for_later, update_action):
    article = ArticleFactory.build(id=1, is_for_later=is_for_later)

    url = for_later_action_url(article)

    assert url == reverse(
        "reading:update_article", kwargs={"article_id": 1, "update_action": update_action}
    )


@pytest.mark.parametrize(
    ("tag", "expected_encoded_tag"),
    [
        ("Tag", "Tag"),
        ("Tag with spaces", "Tag%20with%20spaces"),
        ("Cat/Tag", "Cat------Tag"),
        ("Cat/SubCat/Tag", "Cat------SubCat------Tag"),
    ],
)
def test_encode_external_tag(tag: str, expected_encoded_tag: str):
    encoded_tag = encode_external_tag(tag)

    assert encoded_tag == expected_encoded_tag


@pytest.mark.parametrize(
    ("encoded_tag", "expected_decoded_tag"),
    [
        ("Tag", "Tag"),
        ("Tag%20with%20spaces", "Tag with spaces"),
        ("Cat------Tag", "Cat/Tag"),
        ("Cat------SubCat------Tag", "Cat/SubCat/Tag"),
    ],
)
def test_decode_external_tag(encoded_tag: str, expected_decoded_tag: str):
    decoded_tag = decode_external_tag(encoded_tag)

    assert decoded_tag == expected_decoded_tag


def test_markdown():
    rendered_value = markdown("*Hello* **world**!")

    assert rendered_value == "<p><em>Hello</em> <strong>world</strong>!</p>"
