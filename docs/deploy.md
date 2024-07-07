# Deploy

```{admonition} Your feedback is welcomed
:class: note

If you need/want other ways to deploy the project, please let us know [here](https://github.com/Jenselme/legadilo/discussions/146)!
No matter how you deploy the project, we currently expect you to have a reverse proxy in front of it to manage TLS termination.
```

## Easiest way

Currently, the easiest way to run the project is to use docker and docker compose. To do so, clone the project and run:

    docker compose -f production.yml up -d

This will build the most up-to-date image and start it.
The data will be in the `production_postgres_data` volume.
The service will be exposed on port 8000.
You will also need to configure these commands on the CRON of the host to update the feeds at regular intervals:

```
0 * * * * cd LEGADILO && docker compose -f production.yml exec django python manage.py update_feeds |& systemd-cat -t legadilo
0 0 * * 1 cd LEGADILO && docker compose -f production.yml exec django manage.py clearsessions |& systemd-cat -t legadilo
```

You can also add this line to automatically back up the database (backups will be placed in the `production_postgres_data_backups` volume):

```
0 1 * * * cd LEGADILO && docker compose -f production.yml exec postgres /usr/local/bin/backup
```

You can then use the `/usr/local/bin/restore` script to restore them.

## Docker image

We also provide built docker image (it should be updated at each merge on main). You can get the latest version with:

    docker pull rg.fr-par.scw.cloud/legadilo/legadilo-django:latest

You can also get a tagged version like this:

    docker pull rg.fr-par.scw.cloud/legadilo/legadilo-django:24.07.1  # Example tag

The tags are creating following the calendar version pattern: the two first digits are for the year, the second one are for the month and the lasts are incremented at each build. You can find the list of available tags [in GitHub](https://github.com/Jenselme/legadilo/tags).

You will have to set up the CRON as described in the previous section.

## Configuration options

You can configure the project thanks to environment variables.
If you use docker compose, they will be read from `devops/envs/production/django` (Django only configuration) and `devops/envs/production/postgres` (for the database container setup as well as to allow Django to connect to the database).

You can also allow Django to read a `.env` file by setting `DJANGO_READ_DOT_ENV_FILE` to `True`.

```{admonition} These file are not tracked by git
:class: warning

You must supply them yourselves and must not commit them to avoid leaking secrets!
```

If you use something else, provide them the way you like.

```{admonition} More details
:class: note

If you want more details on those, open `settings.py` and look for them. You will see a link to the Django documentation just above their definition.
```

### For the postgresql container

These variables are required for the container to start and create the proper database with the correct user and password.

| Name                |                                                                              |
|---------------------|------------------------------------------------------------------------------|
| `POSTGRES_HOST`     | Host of the database. Use `postgres` for docker compose use.                 |
| `POSTGRES_PORT`     | Port of the database. Use `5432` for docker compose use.                     |
| `POSTGRES_DB`       | Name of the database. Use `legadilo` for docker compose use.                 |
| `POSTGRES_USER`     | User to use to connect to the database. Use `django` for docker compose use. |
| `POSTGRES_PASSWORD` | Password of the user to connect to the database. Use a safe password!        |


### Required env variables

| Variable name                | Description                                                                                                                                       |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`          | This is used to provide cryptographic signing, should be set to a unique, unpredictable value.                                                    |
| `DJANGO_ALLOWED_HOSTS`       | The domain on which the app is hosted and from which traffic is allowed.                                                                          |
| `DJANGO_DEFAULT_FROM_EMAIL`  | Email used as from unless otherwise specified.                                                                                                    |
| `ADMIN_URL`                  | To change the default admin URL in production for security reason. Will default to `/admin/` in dev.                                              |
| `ACCOUNT_ALLOW_REGISTRATION` | Whether to enable account registration on the instance or not. If disabled, you will have to create the user in the Django admin or with the CLI. |
| `DATABASE_URL`               | The URL to the database formatted like this: postgres://POSTGRES_USER:POSTGRES_PASSWORD@POSTGRES_HOST:POSTGRES_PORT/POSTGRES_DB                   |

```{admonition} DATABASE_URL
:class: note

If you use the env files, the `postgres` file will be loaded first. In it, you already define the database connection settings. You can reuse them like this:
`DATABASE_URL="postgres://${POSTGRES_USER:-}:${POSTGRES_PASSWORD:-}@${POSTGRES_HOST:-}:${POSTGRES_PORT:-}/${POSTGRES_DB:-}"`
```


```{admonition} Creating secrets
:class: note

You can create cryptahpicaly sure secrets in Python with `python3 -c "import secrets; print(secrets.token_urlsafe(60))"`
```

### Other variables

| Variable name                           | Default value      | Description                                                                            |
|-----------------------------------------|--------------------|----------------------------------------------------------------------------------------|
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True`             | See https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains |
| `DJANGO_SECURE_HSTS_PRELOAD`            | `True`             | See https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload            |
| `DJANGO_SERVER_EMAIL`                   | DEFAULT_FROM_EMAIL | The email address that error messages come from.                                       |
| `DJANGO_EMAIL_SUBJECT_PREFIX`           | `[Legadilo]`       | Each email will be prefixed by this.                                                   |
| `EMAIL_HOST`                            | `mailpit`          | On which host to connect to send an email. Leave the default to not send in production |
| `EMAIL_PORT`                            | 1025               | On which port to connect to send an email.                                             |
| `EMAIL_TIMEOUT`                         | 30                 | Max time to wait for when trying to send an email before failing.                      |
| `SENTRY_DSN`                            | `None`             | To enable error monitoring with Sentry (leave empty to leave it deactivated).          |
