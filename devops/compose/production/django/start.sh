#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

readonly GUNICORN_SERVER_HOST=${GUNICORN_SERVER_HOST:-0.0.0.0}
readonly GUNICORN_SERVER_PORT=${GUNICORN_SERVER_PORT:-8000}
readonly GUNICORN_NB_WORKERS=${GUNICORN_NB_WORKERS:-4}
readonly GUNICORN_REQUEST_TIMEOUT=${GUNICORN_REQUEST_TIMEOUT:-60}

python manage.py createcachetable
python manage.py migrate

cmd="${1:-server}"

case "${cmd}" in
    server)
        echo "Starting server on port ${GUNICORN_SERVER_PORT}"
        if [[ "${BUILD_ENV}" == "local" ]]; then
            exec python manage.py runserver "${GUNICORN_SERVER_HOST}:${GUNICORN_SERVER_PORT}"
        else
            exec gunicorn config.wsgi:application \
                --bind "${GUNICORN_SERVER_HOST}:${GUNICORN_SERVER_PORT}" \
                --timeout "${GUNICORN_REQUEST_TIMEOUT}" \
                --workers "${GUNICORN_NB_WORKERS}"
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
