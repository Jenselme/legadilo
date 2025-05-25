docker-cmd := "docker"
docker-compose-cmd := "docker compose"

update-python-deps:
    uv sync --upgrade --all-groups

dev:
    {{docker-compose-cmd}} -f local.yml up

clean-dev-container:
    {{docker-compose-cmd}} -f local.yml down

[working-directory: 'browser-extension']
build-browser-extension:
    npm run build

release:
    #!/usr/bin/env bash
    set -eu

    if [[ $(git branch --show-current) != "main" ]]; then
        echo "You must run the release script on the main branch" >&2
        exit 1
    fi

    base_date_tag=$(date +%y.%m)
    last_tag=$(git tag  | sort -r | grep "${base_date_tag}"  | head -n 1)
    last_tag_revision=$(echo "${last_tag}" | cut -d . -f 3 -)
    new_tag_revision=$((last_tag_revision+1))
    new_tag="${base_date_tag}.${new_tag_revision}"

    echo "Creating version ${new_tag} Press enter to accept."
    read -r

    {{docker-cmd}} pull python:3.13-slim-bookworm
    {{docker-compose-cmd}} -f production.yml build --build-arg "VERSION=${new_tag}" django
    {{docker-cmd}} image tag legadilo_production_django:latest "rg.fr-par.scw.cloud/legadilo/legadilo-django:${new_tag}"
    {{docker-cmd}} image tag legadilo_production_django:latest rg.fr-par.scw.cloud/legadilo/legadilo-django:latest
    {{docker-cmd}} image push "rg.fr-par.scw.cloud/legadilo/legadilo-django:${new_tag}"
    {{docker-cmd}} image push rg.fr-par.scw.cloud/legadilo/legadilo-django:latest
    git tag "${new_tag}"
    git push --tags --no-verify
