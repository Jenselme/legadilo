#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

# Create user to use to run in production.
addgroup --system django
adduser --system --ingroup django django

# Install required system dependencies and updates.
apt-get update
apt-get upgrade -y
# Translations dependencies
apt-get install --no-install-recommends -y gettext

if [[ "${BUILD_ENV}" == "local" ]]; then
    # devcontainer dependencies and utils
    apt-get install --no-install-recommends -y sudo git bash-completion nano ssh nodejs
    # Create devcontainer user and add it to sudoers
    groupadd --gid 1000 dev-user
    useradd --uid 1000 --gid dev-user --shell /bin/bash --create-home dev-user
    echo dev-user ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/dev-user
    chmod 0440 /etc/sudoers.d/dev-user
fi

# cleaning up unused files
apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false
rm -rf /var/lib/apt/lists/*
