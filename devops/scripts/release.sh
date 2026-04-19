#!/usr/bin/env bash

#
# SPDX-FileCopyrightText: 2026 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#


set -eu
set -o pipefail

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
just build-production-images
docker image tag legadilo_production_django:latest "rg.fr-par.scw.cloud/legadilo/legadilo-django:${new_tag}"
docker image tag legadilo_production_django:latest rg.fr-par.scw.cloud/legadilo/legadilo-django:latest
docker image push "rg.fr-par.scw.cloud/legadilo/legadilo-django:${new_tag}"
docker image push rg.fr-par.scw.cloud/legadilo/legadilo-django:latest
git tag "${new_tag}"
git push --follow-tags --no-verify
