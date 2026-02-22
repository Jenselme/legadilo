# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.db.models import CharField, EmailField, Func, IntegerField
from django.db.models.functions import Length

from .timezone import Timezone

__all__ = ["Timezone"]

CharField.register_lookup(Length)


class CaseInsensitiveEmailField(EmailField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_collation = "nocase"


class ExtractEpoch(Func):
    def as_postgresql(self, compiler, connection, **extra_context):
        return self.as_sql(
            compiler,
            connection,
            function="EXTRACT",
            template="%(function)s(EPOCH FROM %(expressions)s)",
            **extra_context,
        )

    def as_sqlite(self, compiler, connection, **extra_context):
        extra_context.setdefault("output_field", IntegerField())
        return self.as_sql(
            compiler,
            connection,
            function="STRFTIME",
            # The string will be formatted with % twice!
            template=r"%(function)s('%%%%s', %(expressions)s)",
            **extra_context,
        )
