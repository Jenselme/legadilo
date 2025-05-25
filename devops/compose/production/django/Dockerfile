FROM node:lts-slim AS node-builder

COPY ./package.json /
COPY ./package-lock.json /

RUN cd / && npm install

FROM python:3.13-slim-bookworm AS python-builder

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app
ARG PYTHONDEVMODE=''
ARG VERSION=''

ENV UV_LINK_MODE copy
ENV UV_COMPILE_BYTECODE 1
ENV UV_PYTHON_DOWNLOADS never
ENV UV_PROJECT_ENVIRONMENT ${APP_HOME}/.venv
ENV UV_PYTHON /usr/local/bin/python
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONDEVMODE ${PYTHONDEVMODE}
ENV BUILD_ENV ${BUILD_ENVIRONMENT}
ENV VERSION ${VERSION}
# make sure we use the virtualenv by default
ENV PATH "${APP_HOME}/.venv/bin:$PATH"

WORKDIR ${APP_HOME}

COPY ./devops/compose/production/django/setup-container.sh /
RUN chmod +x /setup-container.sh
RUN /setup-container.sh

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,readonly \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,readonly \
    uv sync --locked --no-install-project --group prod --no-group dev --no-group doc

COPY . ${APP_HOME}
COPY --from=node-builder /node_modules/ ${APP_HOME}/node_modules/

COPY ./devops/compose/production/django/setup-django.sh /
RUN chmod +x /setup-django.sh
RUN /setup-django.sh


FROM python:3.13-slim-bookworm

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app
ARG PYTHONDEVMODE=''
ARG VERSION=''

ENV UV_LINK_MODE copy
ENV UV_COMPILE_BYTECODE 1
ENV UV_PYTHON_DOWNLOADS never
ENV UV_PROJECT_ENVIRONMENT ${APP_HOME}/.venv
ENV UV_PYTHON /usr/local/bin/python
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONDEVMODE ${PYTHONDEVMODE}
ENV BUILD_ENV ${BUILD_ENVIRONMENT}
ENV VERSION ${VERSION}
# make sure we use the virtualenv by default
ENV PATH "${APP_HOME}/.venv/bin:$PATH"

WORKDIR ${APP_HOME}

RUN <<EOT
# Create user to use to run in production.
addgroup --system django
adduser --system --ingroup django django

apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    gettext
apt-get upgrade -y

apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOT

COPY --chown=django:django ./devops/compose/production/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --chown=django:django ./devops/compose/production/django/start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start.sh"]

USER django

# copy application code to WORKDIR
COPY --from=python-builder --chown=django:django ${APP_HOME} ${APP_HOME}
