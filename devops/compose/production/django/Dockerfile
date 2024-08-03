FROM node:lts-slim AS node

COPY ./package.json /
COPY ./package-lock.json /

RUN cd / && npm install

FROM python:3.12-slim-bookworm

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app
ARG PYTHONDEVMODE=''
ARG VERSION=''

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONDEVMODE ${PYTHONDEVMODE}
ENV BUILD_ENV ${BUILD_ENVIRONMENT}
ENV CREATE_VENV 0
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

COPY ./devops/compose/production/django/setup-project.sh /
COPY pyproject.toml .
COPY poetry.lock .
RUN chmod +x /setup-project.sh
RUN /setup-project.sh

COPY --chown=django:django ./devops/compose/production/django/setup-django.sh /

# copy application code to WORKDIR
COPY --chown=django:django . ${APP_HOME}
COPY --from=node --chown=django:django /node_modules/ ${APP_HOME}/node_modules/

# make django owner of the WORKDIR directory as well.
RUN chown django:django ${APP_HOME}

USER django

RUN chmod +x /setup-django.sh
RUN /setup-django.sh
