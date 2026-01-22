# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from .pwa_views import default_favicon_view, manifest_view
from .utils_views import security_txt_view

__all__ = ["default_favicon_view", "manifest_view", "security_txt_view"]
