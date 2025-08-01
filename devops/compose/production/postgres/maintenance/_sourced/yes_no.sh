# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# shellcheck shell=bash

yes_no() {
    # shellcheck disable=2034
    declare desc="Prompt for confirmation. \$\"\{1\}\": confirmation message."
    local arg1="${1}"

    local response=
    read -r -p "${arg1} (y/[n])? " response
    if [[ "${response}" =~ ^[Yy]$ ]]
    then
        exit 0
    else
        exit 1
    fi
}
