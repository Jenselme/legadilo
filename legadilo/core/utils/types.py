# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# This is for: (TotalNbModelsDeleted, {"RelatedModel": NbDeleted, "Model": NbDeleted})
type DeletionResult = tuple[int, dict[str, int]]
type FormChoice = tuple[str, str]
type FormChoices = list[FormChoice]
