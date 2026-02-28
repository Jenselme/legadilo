# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

default:
    just --list

update-python-deps:
    uv sync --upgrade --all-groups
    pre-commit run -a
    uv run pytest
    git commit uv.lock -m "chore: update deps"

update-js-deps:
    npm update

dev:
    docker compose -f local.yml up


dev-local-python:
    docker compose -f local.yml --profile mail up -d
    python manage.py runserver


dev-local-python-pg:
    docker compose -f local.yml --profile postgres --profile mail up -d postgres mailpit
    DATABASE_URL="postgres://django:django_passwd@localhost:5432/legadilo" python manage.py runserver

update-feeds:
    uv run python manage.py update_feeds

setup-dev-database:
    uv run python manage.py migrate
    uv run python manage.py setup_test_db


setup-ci:
    sudo apt-get update
    sudo apt-get install -y gettext
    uv sync --dev --locked

test:
    uv run pytest

test-coverage:
    uv run pytest --cov --cov-report term:skip-covered --cov-fail-under=90

lint:
    uv run pre-commit run -a

makemigrations:
    uv run python manage.py makemigrations

migrate:
    uv run python manage.py createcachetable
    uv run python manage.py migrate

migrate-pg:
    DATABASE_URL="postgres://django:django_passwd@localhost:5432/legadilo" uv run python manage.py migrate

clean-dev-container:
    docker compose -f local.yml down

update-po:
    uv run python manage.py makemessages --all --no-location

compile-po:
    uv run python manage.py compilemessages

[working-directory('browser-extension')]
build-browser-extension:
    npm run build

release:
    #!/usr/bin/env bash
    set -eu

    if [[ $(git branch --show-current) != "main" ]]; then
        echo "You must run the release script on the main branch" >&2
        exit 1
    fi

    docker login rg.fr-par.scw.cloud/legadilo -u nologin --password-stdin < ~/.private/scw-registry-password
    base_date_tag=$(date +%y.%m)
    last_tag=$(git tag  | sort -r | grep "${base_date_tag}"  | head -n 1)
    last_tag_revision=$(echo "${last_tag}" | cut -d . -f 3 -)
    new_tag_revision=$((last_tag_revision+1))
    new_tag="${base_date_tag}.${new_tag_revision}"

    sed -Ei "s/^version = \"[1-9]{2}\.[0-9]{2}\.[0-9]\"$/version = \"${new_tag}\"/g" pyproject.toml
    sed -i "s/## Unreleased$/## Unreleased\n\n## ${new_tag}/g" CHANGELOG.md
    uv lock
    echo "Creating version ${new_tag} Press enter to accept."
    read -r

    git commit -am "chore: releasing ${new_tag}"
    docker pull python:3.14-slim-trixie
    docker compose -f production.yml build django
    docker image tag legadilo_production_django:latest "rg.fr-par.scw.cloud/legadilo/legadilo-django:${new_tag}"
    docker image tag legadilo_production_django:latest rg.fr-par.scw.cloud/legadilo/legadilo-django:latest
    docker image push "rg.fr-par.scw.cloud/legadilo/legadilo-django:${new_tag}"
    docker image push rg.fr-par.scw.cloud/legadilo/legadilo-django:latest
    git tag "${new_tag}"
    git push --follow-tags --no-verify
