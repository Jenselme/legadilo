FROM python:3.13-slim-bookworm

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app
ARG PYTHONDEVMODE=1

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
# make sure we use the virtualenv by default
ENV PATH "${APP_HOME}/.venv/bin:$PATH"

WORKDIR ${APP_HOME}

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY ./devops/compose/production/django/setup-container.sh /
RUN chmod +x /setup-container.sh
RUN /setup-container.sh

COPY ./devops/compose/production/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./devops/compose/production/django/start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start.sh"]

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,readonly \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,readonly \
    uv sync --locked --no-install-project --dev

COPY ./devops/compose/production/django/setup-django.sh /
RUN chmod +x /setup-django.sh
RUN /setup-django.sh
