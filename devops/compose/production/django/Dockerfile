FROM node:lts-slim AS node-builder

COPY ./package.json /
COPY ./package-lock.json /

RUN cd / && npm install

FROM python:3.12-slim-bookworm

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app
ARG PYTHONDEVMODE=''
ARG VERSION=''

ENV UV_LINK_MODE copy
ENV UV_COMPILE_BYTECODE 1
ENV UV_PYTHON_DOWNLOADS never
ENV UV_PROJECT_ENVIRONMENT ${APP_HOME}/.venv
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONDEVMODE ${PYTHONDEVMODE}
ENV BUILD_ENV ${BUILD_ENVIRONMENT}
ENV VERSION ${VERSION}

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

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --group prod --no-group dev --no-group doc

COPY --chown=django:django ./devops/compose/production/django/setup-django.sh /

# copy application code to WORKDIR
COPY --chown=django:django . ${APP_HOME}
COPY --from=node-builder --chown=django:django /node_modules/ ${APP_HOME}/node_modules/

# make sure we use the virtualenv by default
ENV PATH "${APP_HOME}/.venv/bin:$PATH"

RUN chmod +x /setup-django.sh
RUN /setup-django.sh

# make django owner of the WORKDIR directory as well.
RUN chown django:django ${APP_HOME}

USER django
