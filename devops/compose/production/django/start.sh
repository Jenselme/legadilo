#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python manage.py createcachetable
python manage.py migrate

if [[ "${BUILD_ENV}" == "local" ]]; then
    exec python manage.py runserver 0.0.0.0:8000
else
    exec daphne config.asgi:application -b 0.0.0.0 -p 8000
fi
