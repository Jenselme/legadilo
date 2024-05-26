#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

if [[ "${BUILD_ENV}" == "local" ]]; then
    echo "Nothing to do for local build"
else
    DATABASE_URL="" \
      DJANGO_SETTINGS_MODULE="config.settings" \
      DJANGO_SECRET_KEY="test" \
      DJANGO_ADMIN_URL="/admin" \
      python manage.py compilemessages

    DATABASE_URL="" \
      DJANGO_SETTINGS_MODULE="config.settings" \
      DJANGO_SECRET_KEY="test" \
      DJANGO_ADMIN_URL="/admin" \
      python manage.py collectstatic \
        --clear \
        --ignore 'bootstrap.rtl*' \
        --ignore 'bootstrap-*' \
        --ignore 'bootstrap.bundle.*' \
        --ignore 'bootstrap.esm.*' \
        --ignore 'debug_toolbar' \
        --ignore 'django-browser-reload' \
        --ignore '*.html' \
        --ignore '*.scss' \
        --ignore 'ext' \
        --no-input
fi
