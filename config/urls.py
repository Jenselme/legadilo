# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views

from config.api import api


def _correct_admin_url(path: str) -> str:
    path = path.removeprefix("/")

    if not path.endswith("/"):
        path += "/"

    return path


urlpatterns = [  # noqa: RUF005 concatenation
    path("", include("legadilo.website.urls", namespace="website")),
    # Django Admin, use {% url 'admin:index' %}
    # Make sure it's correct no matter how it's configured in the env.
    path(_correct_admin_url(settings.ADMIN_URL), admin.site.urls),
    # User management
    path("users/", include("legadilo.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path("feeds/", include("legadilo.feeds.urls", namespace="feeds")),
    path("reading/", include("legadilo.reading.urls", namespace="reading")),
    path("import-export/", include("legadilo.import_export.urls", namespace="import_export")),
    path("api/", api.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [  # type: ignore[assignment] # noqa: RUF005 concatenation
            path("__debug__/", include(debug_toolbar.urls))
        ] + urlpatterns  # type: ignore[operator]
    if "django_browser_reload" in settings.INSTALLED_APPS:
        urlpatterns.append(path("__reload__/", include("django_browser_reload.urls")))
