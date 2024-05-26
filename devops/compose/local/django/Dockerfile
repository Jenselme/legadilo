FROM python:3.12-slim-bookworm

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app
ARG PYTHONDEVMODE=1

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONDEVMODE ${PYTHONDEVMODE}
ENV BUILD_ENV ${BUILD_ENVIRONMENT}
ENV CREATE_VENV 0

WORKDIR ${APP_HOME}

COPY ./devops/compose/production/django/setup-container.sh /
RUN chmod +x /setup-container.sh
RUN /setup-container.sh

COPY ./devops/compose/production/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./devops/compose/production/django/start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start.sh"]

COPY ./devops/compose/production/django/setup-project.sh /
COPY pyproject.toml .
COPY poetry.lock .
COPY README.md .
RUN chmod +x /setup-project.sh
RUN /setup-project.sh

COPY ./devops/compose/production/django/setup-django.sh /
RUN chmod +x /setup-django.sh
RUN /setup-django.sh
