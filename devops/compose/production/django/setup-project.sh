#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

# Install Python deps
pip install -U pip
pip install poetry==1.8.2
if [[ "${CREATE_VENV}" != "1" ]]; then
    poetry config virtualenvs.create false
fi

if [[ "${BUILD_ENV}" == "local" ]]; then
    poetry install --no-interaction --with dev --with typing
else
    poetry install --no-interaction --with prod
fi
