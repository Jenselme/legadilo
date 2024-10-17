#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python manage.py createcachetable
python manage.py migrate

cmd="${1:-server}"

case "${cmd}" in
    server)
        SERVER_PORT=8000
        echo "Starting server on port ${SERVER_PORT}"
        if [[ "${BUILD_ENV}" == "local" ]]; then
            exec python manage.py runserver 0.0.0.0:${SERVER_PORT}
        else
            exec daphne config.asgi:application --bind 0.0.0.0 --port ${SERVER_PORT} --no-server-name --verbosity 1
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
