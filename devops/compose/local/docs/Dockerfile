FROM python:3.12-slim-bookworm

ARG BUILD_ENVIRONMENT
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update && apt-get install --no-install-recommends -y \
  # To run the Makefile
  make \
  # Translations dependencies
  gettext \
  # Uncomment below lines to enable Sphinx output to latex and pdf
  # texlive-latex-recommended \
  # texlive-fonts-recommended \
  # texlive-latex-extra \
  # latexmk \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
COPY poetry.lock .
RUN pip install -U pip && \
    pip install poetry==1.8.2 && \
    poetry config virtualenvs.create false && \
    poetry install --with dev --with typing --with doc

COPY ./devops/compose/local/docs/start.sh /start-docs.sh
RUN chmod +x /start-docs.sh

WORKDIR /docs
