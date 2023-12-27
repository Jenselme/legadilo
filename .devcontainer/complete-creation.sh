#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset


# For VSCode extension used to edit sphinx projects.
pip install esbonio

python manage.py createcachetable
python manage.py migrate

cat .devcontainer/bashrc.override.sh >> ~/.bashrc

function setup-pre-commit() {
    while [[ ! -f ~/.gitconfig ]]; do
        echo "Waiting for git config to become available."
        sleep 30
    done

    pre-commit install
}

# Run in the backend to allow VSCode to configure git.
setup-pre-commit &
