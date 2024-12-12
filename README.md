# Legadilo

Read your RSS feeds & save other articles

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Black code style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Legadilo](https://www.legadilo.eu/) is a project to help you subscribe to RSS feeds, save articles and organize them easily with tags and full customizable reading lists! It’s written with the [Django web framework](https://www.djangoproject.com/), [the boostrap 5 frontend toolkit](https://getbootstrap.com/) and with enhancements given by [htmx](https://htmx.org/).

It’s opensource under [the GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html#license-text) and is designed to be self-hostable, so you can run your own instance.
Your [ideas](https://github.com/Jenselme/legadilo/issues/new), [contributions](https://github.com/Jenselme/legadilo/pulls) and [feedback](https://github.com/Jenselme/legadilo/discussions) are welcomed! You can also check the [official instance](https://www.legadilo.eu/) to start using it more easily (you will be able to export and import your data in any instance)! If you contribute, don’t forget to add yourselves to the `CONTRIBUTORS.txt` file.

## Developing

### Start the project locally

1. Ensure you have [Docker](https://www.docker.com/) and [node](https://nodejs.org/en) installed.
2. Run `npm install` to install our few JS deps.
3. Run `docker compose -f local.yml up`
4. The site should be accessible at http://localhost:8000

### Using VSCode

You can rely on the `devcontainer.json` file to start the project and develop teh project inside a container. This way, you don’t need to install anything on your machine to make it work (besides docker). VSCode should propose you continue in a container the first time you open the project and will take care of the rest for you. See [here](https://containers.dev/supporting) for more.

You will have to start Django with the provided run target.

### Using Pycharm

By default, everything is set up to develop locally with Pycharm. So you will need docker (for the database), [uv](https://docs.astral.sh/uv/), Python 3.12 and nodeJS 20+ installed for this to work.
Django will be started automatically.
On the first run, you must run `npm install` to install a few JS deps and `uv run pre-commit install --hook-type pre-commit --hook-type pre-push` to configure `pre-commit`.

You should also be able to use devcontainers but the support is more recent and isn’t as good as in VSCode according to my tests.
See [here](https://www.jetbrains.com/help/pycharm/connect-to-devcontainer.html) for more.

### Project structure

- The code of the Django project is in the `legadilo/`.
- The settings file, main urls file are in the `config/`.
- The doc is in `docs/` It’s built with sphinx and mostly written in [MyST](https://myst-parser.readthedocs.io/en/v0.15.1/index.html) (MyST is a rich and extensible flavor of Markdown meant for technical documentation and publishing).
- Scripts to do a release, dockerfiles and default env file are in `devops/`
- Docker compose configurations are in `local.yml` for local development and `production.yml` for running the project in production.
- `manage.py` is Django commands’ main entry point.
- `locale/` will be used to translate the project. Currently, we only mark the strings for translation.
- `.github/` is used to configure dependabot and the CI.
- `.app-template/` is used by Django to create a new app.
- `.decontainer/`, `.idea/`, `.vscode/` and `.editorconfig` are editors configuration.
- `.eslintrc.json`, `prettierrc.json` and `.stylelintrc.json` contains the JS/CSS linters and formatters configurations.
- `pyproject.toml` defines the Python dependencies and is used to configure Python linting tools.
- `uv.lock` and `package-lock.json` are used to lock the dependencies.

### Basic Commands

All these commands must be run at the root of the project!

- Run the server: `uv run python manage.py runserver`
- Create migrations files after updating models: `uv run python manage.py makemigrations`
- Apply migrations: `uv run python manage.py migrate`
- Create a _superuser_: `uv run python manage.py createsuperuser`

### Email Server

In development, it is often nice to be able to see emails that are being sent from your application. For that reason local SMTP server [Mailpit](https://github.com/axllent/mailpit) with a web interface is available as docker container.

Container mailpit will start automatically when you will run all docker containers.
Please check [cookiecutter-django Docker documentation](http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html) for more details how to start all containers.

With Mailpit running, to view messages that are sent by your application, open your browser and go to `http://127.0.0.1:8025`

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to Mailpit to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.
- To create a **superuser account**, use this command:

      $ uv run python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Writing code

All code should be tested and type annotated. We use [pytest](https://docs.pytest.org/en/8.2.x/) as our test runner and [mypy](https://mypy-lang.org/) as our type checker. We use [ruff](https://docs.astral.sh/ruff/) to lint and format our code. You can:

- Run mypy like this: `pre-commit run mypy -a`
- Run tests like this: `pytest` (note: both VSCode and Pycharm should be able to run the tests natively)
- Run the linter: `pre-commit run ruff -a` (this should be done automatically on save)
- Format the Python file: `pre-commit run ruff-format` (this should be done automatically on save)
- Format HTML files: `pre-commit run djlint-reformat-django`

### Commiting

To ease development, we use [pre-commit](https://pre-commit.com/) to run all our linters before each commit.

We try to follow the same [rules as the angular project](https://github.com/angular/angular.js/blob/master/DEVELOPERS.md#-git-commit-guidelines>) towards commits. Each commit is constituted from a summary line, a body and eventually a footer. Each part are separated with a blank line.

The summary line is as follows: `<type>(<scope>): <short description>`. It must not end with a dot and must be written in present imperative. Don't capitalize the fist letter. The whole line shouldn't be longer than 80 characters and if possible be between 70 and 75 characters. This is intended to have better logs.

The possible types are:
- `chore` for changes in the build process or auxiliary tools.
- `doc` for documentation
- `feat` for new features
- `ref`: for refactoring
- `style` for modifications that not change the meaning of the code.
- `test`: for tests

The body should be written in imperative. It can contain multiple paragraph. Feel free to use bullet points.

Use the footer to reference issue, pull requests or other commits.

This is a full example:

```
feat(css): use CSS sprites to speed page loading

- Generate sprites with the gulp-sprite-generator plugin.
- Add a build-sprites task in gulpfile

Close #24
```

Browse [the project history](https://github.com/Jenselme/legadilo/commits/main/) to see how contributors last did it in the past!

#### Create a new app

Apps are useful to structure the project. To create a new one, use the commands below:

```
APP_NAME=<APP_NAME>
mkdir legadilo/$APP_NAME
django-admin startapp --template .app-template $APP_NAME legadilo/$APP_NAME
```

Don’t forget to add it to `INSTALLED_APPS`!


## Deployment

See [this page](./docs/deploy.md).
