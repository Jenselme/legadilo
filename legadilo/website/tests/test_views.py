# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from http import HTTPStatus

from django.urls import reverse


def test_manifest_view(client):
    response = client.get(reverse("website:manifest"))

    assert response.status_code == HTTPStatus.OK
    assert response["Content-Type"] == "application/json"
    assert isinstance(json.loads(response.content.decode("utf-8")), dict)
