#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python manage.py createcachetable
python manage.py migrate

if [[ "${BUILD_ENV}" == "local" ]]; then
    exec python manage.py runserver 0.0.0.0:8000
else
    exec daphne config.asgi:application --bind 0.0.0.0 --port  --no-server-name
fi
