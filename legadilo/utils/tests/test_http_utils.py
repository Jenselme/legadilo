# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.http import QueryDict

from legadilo.utils.http_utils import dict_to_query_dict


def test_dict_to_query_dict():
    assert dict_to_query_dict({"a": 1, "b": [2, 3]}) == QueryDict("a=1&b=2&b=3")
