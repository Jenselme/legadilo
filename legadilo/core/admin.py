# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin

from legadilo.core.models import Timezone


@admin.register(Timezone)
class TimezoneAdmin(admin.ModelAdmin):
    search_fields = ["name"]
