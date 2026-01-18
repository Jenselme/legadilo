# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from types import MappingProxyType

from django.utils.translation import gettext_lazy as _

INVALID_USERS_RETENTION_DAYS = 30
USER_SETTINGS_PAGES = MappingProxyType({
    "users:update": _("My Infos"),
    "account_email": _("E-Mail"),
    "account_change_password": _("Change password"),
    "users:update_settings": _("My settings"),
    "mfa_index": _("Two-Factor Authentication"),
    "users:manage_tokens": _("Manage application tokens"),
    "import_export:import_export_articles": _("Import/Export Articles"),
})
