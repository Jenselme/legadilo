# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.db.models import CharField, DateTimeField
from django.db.models.functions import Extract, Length

from .timezone import Timezone

__all__ = ["Timezone"]

CharField.register_lookup(Length)


class ExtractTs(Extract):
    lookup_name = "epoch"


DateTimeField.register_lookup(ExtractTs)
