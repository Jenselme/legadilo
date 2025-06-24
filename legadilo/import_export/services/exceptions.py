# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later


class DataImportError(Exception):
    pass


class InvalidEntryError(DataImportError):
    pass
