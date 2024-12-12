#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset


# For VSCode extension used to edit sphinx projects.
pip install esbonio

uv run python manage.py createcachetable
uv run python manage.py migrate

npm install

cat .devcontainer/bashrc.override.sh >> ~/.bashrc

function setup-pre-commit() {
    while [[ ! -f ~/.gitconfig ]]; do
        echo "Waiting for git config to become available."
        sleep 30
    done

    uv run pre-commit install --hook-type pre-commit --hook-type pre-push
}

# Run in the backend to allow VSCode to configure git.
setup-pre-commit &
