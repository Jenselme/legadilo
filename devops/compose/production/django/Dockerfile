# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

FROM node:lts-slim AS node-builder

COPY ./package.json /
COPY ./package-lock.json /

RUN cd / && npm install

FROM python:3.13-slim-bookworm AS python-builder

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app
ARG PYTHONDEVMODE=''

ENV UV_LINK_MODE copy
ENV UV_COMPILE_BYTECODE 1
ENV UV_NO_MANAGED_PYTHON 1
ENV UV_PYTHON_DOWNLOADS never
ENV UV_PROJECT_ENVIRONMENT ${APP_HOME}/.venv
ENV UV_PYTHON /usr/local/bin/python
ENV UV_REQUIRE_HASHES 1
ENV UV_VERIFY_HASHES 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONDEVMODE ${PYTHONDEVMODE}
ENV BUILD_ENV ${BUILD_ENVIRONMENT}
# Some deps are install with git, so git must be installed here for the deps to be installed.
# Don't install it on the image that will run the code since it increases the size by ~100MB.
ENV INSTALL_GIT 1
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

COPY ./devops/compose/production/django/build-django.sh /
RUN chmod +x /build-django.sh
RUN /build-django.sh


FROM python:3.13-slim-bookworm

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app
ARG PYTHONDEVMODE=''

ENV UV_LINK_MODE copy
ENV UV_COMPILE_BYTECODE 1
ENV UV_PYTHON_DOWNLOADS never
ENV UV_PROJECT_ENVIRONMENT ${APP_HOME}/.venv
ENV UV_PYTHON /usr/local/bin/python
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONDEVMODE ${PYTHONDEVMODE}
ENV BUILD_ENV ${BUILD_ENVIRONMENT}
# make sure we use the virtualenv by default
ENV PATH "${APP_HOME}/.venv/bin:$PATH"

WORKDIR ${APP_HOME}

COPY ./devops/compose/production/django/setup-container.sh /
RUN chmod +x /setup-container.sh
RUN /setup-container.sh

COPY --chown=django:django ./devops/compose/production/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --chown=django:django ./devops/compose/production/django/start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start.sh"]

USER django

# copy application code to WORKDIR
COPY --from=python-builder --chown=django:django ${APP_HOME} ${APP_HOME}
