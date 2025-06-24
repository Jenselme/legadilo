#!/bin/bash

# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -o errexit
set -o pipefail
set -o nounset

exec uv run make livehtml
