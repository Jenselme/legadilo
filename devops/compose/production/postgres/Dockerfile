FROM postgres:17

COPY ./devops/compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
RUN apt-get update && \
      apt-get upgrade -y && \
      apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
      rm -rf /var/lib/apt/lists/*
