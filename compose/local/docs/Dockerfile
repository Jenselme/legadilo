FROM python:3.12-slim-bullseye

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
    pip install poetry==1.7.1 && \
    poetry install --with dev

COPY ./compose/local/docs/start /start-docs
RUN sed -i 's/\r$//g' /start-docs
RUN chmod +x /start-docs

WORKDIR /docs
