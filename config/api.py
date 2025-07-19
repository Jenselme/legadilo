# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from ninja import NinjaAPI
from ninja.security import django_auth

from legadilo.feeds.api import feeds_api_router
from legadilo.import_export.api import export_api_router
from legadilo.reading.api import reading_api_router
from legadilo.users.api import AuthBearer, users_api_router

api = NinjaAPI(title="Legadilo API", auth=[AuthBearer(), django_auth], docs_url="/docs/")
api.add_router("reading/", reading_api_router)
api.add_router("feeds/", feeds_api_router)
api.add_router("users/", users_api_router)
api.add_router("export/", export_api_router)
