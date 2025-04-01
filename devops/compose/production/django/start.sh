#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

readonly SERVER_PORT=8000
readonly NB_GUNICORN_WORKERS=4
readonly GUNICORN_REQUEST_TIMEOUT=60

python manage.py createcachetable
python manage.py migrate

cmd="${1:-server}"

case "${cmd}" in
    server)
        echo "Starting server on port ${SERVER_PORT}"
        if [[ "${BUILD_ENV}" == "local" ]]; then
            exec python manage.py runserver "0.0.0.0:${SERVER_PORT}"
        else
            exec gunicorn config.wsgi:application --bind "0.0.0.0:${SERVER_PORT}" --timeout ${GUNICORN_REQUEST_TIMEOUT} --workers ${NB_GUNICORN_WORKERS}
        fi
        ;;
    cron)
        exec python manage.py cron
        ;;
    *)
        echo "Unknown command" >&2
        exit 1
        ;;
esac
