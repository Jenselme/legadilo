#!/usr/bin/env bash

set -eu

base_date_tag=$(date +%y.%m)
last_tag=$(git tag  | sort -r | grep "${base_date_tag}"  | head -n 1)
last_tag_revision=$(echo "${last_tag}" | cut -d . -f 3 -)
new_tag_revision=$((last_tag_revision+1))
new_tag="${base_date_tag}.${new_tag_revision}"

echo "Creating version ${new_tag} Press enter to accept."
read -r

docker compose -f production.yml build django
docker image tag legadilo_production_django:latest "rg.fr-par.scw.cloud/legadilo/legadilo-django:${new_tag}"
docker image tag legadilo_production_django:latest rg.fr-par.scw.cloud/legadilo/legadilo-django:latest
docker image push "rg.fr-par.scw.cloud/legadilo/legadilo-django:${new_tag}"
docker image push rg.fr-par.scw.cloud/legadilo/legadilo-django:latest
git tag "${new_tag}"
git push --tags --no-verify
