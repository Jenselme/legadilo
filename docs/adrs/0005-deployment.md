<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 5 - Deployment

* **Date:** 2024-07-06
* **Status:** Accepted


## Context

We want something as flexible as possible while using as few services as possible to keep things simple, ease deployment outside docker compose and reduce memory and CPU footprint. After some testing, here are some interesting results:
- [Whitenoise](https://whitenoise.readthedocs.io/en/latest/) can serve static files efficiently:
  - It sets the proper caching header and compress the files with gzip.
  - It can serve multiple requests in parallel even under WSGI. Tested with `curl --limit-rate 1K http://localhost:8000/static/js/bootstrap.min.3014ed547a4b.js`. 
- [Gunicorn](https://gunicorn.org/): once the view has returned, it can free its worker to process another request even if the response is not fully sent to the client yet. _But_ it has to wait on the view.
- [Daphne](https://github.com/django/daphne) and ASGI are more flexible on that regard: even with one worker they can process more requests. To ease configuration (and take advantages of our async views used to fetch and stream content and receive big file uploads with blocking a thread), it’s probably a good idea to use ASGI instead of WSGI. 


## Decision

Simplify what we can to have as few services as possible. We should only need a container for Django and one for Postgres.
- Rely on [Whitenoise](https://whitenoise.readthedocs.io/en/latest/) to serve static assets.
- Rely on [Daphne](https://github.com/django/daphne) and asgi for throughput.
- Rely on the host and its CRON to run commands at regular interval.


## Consequences

- Both Daphne and Whitenoise are popular and production ready dependencies for what we are trying to do. So no worries on that front.
- Since we are using ASGI, we can expand our async usage if need easily.
- We don’t support TLS termination yet. So the user must rely on a reverse proxy to do it. Good enough for now. We will probably have to allow Daphne to do it with environment variables at some point.
- Once we have some user feedback, we will be able to improve deployments based on true usage.
- We will need another strategy (without CRON or built with docker compose) to run update feeds at regular interval. But we need more feedback before trying to do something in that regard.
