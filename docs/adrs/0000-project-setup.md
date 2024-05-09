# 0 - Project setup

* **Date:** 2023-12-21
* **Status:** Accepted

## Context

The goal of this project is to provide a way to subscribe to RSS feeds and save articles.
All these articles should be arranged nicely to help reading in different situations.
All the data must be searchable so that you can find as easily as possible what you are looking for.
It must be self-hostable easily.

To get started with good default and help me develop this, I already decided to use [Django](https://docs.djangoproject.com/) and to boostrap the project with [this cookiecutter template](https://cookiecutter-django.readthedocs.io/en/latest/).
Since it will involve lots of fetching, I also decided to use Django in a fully async manner.
Besides, I already know Django (which is good to get started quickly and easily) and I intend to use this project for practicing Django and applying some good practices.

This choices were made to ease developing the project. I tested some other frameworks, but none justify moving away from Django for this project: I already know Django and am efficient with it, it doesn’t have drawbacks for what I am building and the project it big enough not to learn a framework in addition to developing it. 

### CSS framework

The template comes with [django-crispy-forms](https://github.com/django-crispy-forms/django-crispy-forms) to help you render form.
It seems like a nice solution and will surely speed up forms writing at the start of the project.
By default, it uses the [Bootstrap](https://getbootstrap.com/) framework to render them.
Since it’s not the only solution, let’s look at a quick comparison of all the frameworks supported by Django crispy form.

I think I can achieve my goals with any of them: they are mature enough and have enough features.
I don’t need (at least right now) any Javascript behavior.
Until I add some pages, changing shouldn’t cost much.
The goal for now is to be able to move fast and test things, so I can validate what I want to do and how I want to do it.

I tested without debug mode (ie without debug toolbar) to get these numbers.
All the frameworks were loaded through a CDN to make things easier.

| Framework  | Transferred size | Size  | Notes                                                                                       |
|------------|------------------|-------|---------------------------------------------------------------------------------------------|
| Nothing    | 9kB              | 18kB  |                                                                                             |
| Bootstrap  | 33kB             | 247kB | JS & CSS                                                                                    |
| Bulma      | 40kB             | 221kB | Only CSS                                                                                    |
| Foundation | 71kB             | 353kB | JS & CSS                                                                                    |
| Tailwind   | 321kB            | 747kB | JS & CSS, the plugin is still in beta, must be installed properly to have a reasonable size |


## Decisions

* **Package management:** [poetry](https://python-poetry.org/). It’s a reliable and popular solution. Dependencies are defined directly in the `pyproject.toml` file (no need for something extra), dependencies are put into groups which you can install or ignore and it provides a lock file for reliable installation. And I use it at work.
* **Linting:**
  * [pre-commit](https://pre-commit.com/) to run checks before each commits as well as on CI. I also enable lots of its default checks.
  * [ruff](https://docs.astral.sh/ruff/) as a linter and formatter. It includes so many things by default that I don’t need anything else. It’s also fast and popular. Let’s put it to the test!
  * [pyupgrade](https://github.com/asottile/pyupgrade) and [django-upgrade](https://github.com/adamchainz/django-upgrade) to help keep the code base up to date.
  * [djLint](https://github.com/Riverside-Healthcare/djLint) and [curlylint](https://github.com/thibaudcolas/curlylint) to format and lint templates.
  * [shellcheck](https://github.com/shellcheck-py/shellcheck-py) to lint shell scripts.
* **Type checking:** [mypy](https://mypy.readthedocs.io/en/stable/index.html) because I’ve used it in the past and it’s kind of a default choice.
* **Test runner:** [pytest](https://docs.pytest.org/en/7.4.x/) with [pytest-django](https://pytest-django.readthedocs.io/en/latest/). Very solid and popular choice in the Python world. It’s kind of a default choice.
* **Repository:** git on GitHub in the hope it will help collaboration.
* **CI:** Raw GitHub actions to keep things simple.
* **Async:** Let’s run everything with [daphne](https://github.com/django/daphne). See [this article](https://www.jujens.eu/posts/en/2023/Dec/10/django-async/#django-async) for a more in depth analysis of the possible solutions. This should help us with article fetching and feed file fetching with many users. It should also make serving static files directly from Python easier.
* **Initial dependencies:** They are either good and well-used within the community and will help me advance quickly or provide small niceties (the ones that add extra checks) I can just remove later easily if needed. The only structuring one is django-crispy-forms, but I won’t even write form code so the early gain of time will compensate for it.
* **CSS framework:** Let’s keep bootstrap from now, it’s good enough and is better supported by crispy forms. I may even remove the JS part if I don’t need it. It’s loaded by a CDN for now to avoid loosing time on this. It also feels way easier to use given what I already know.
* **Doc:** Let’s write relevant documentation and *most importantly* document architecture decisions in ADRs. They will be written in [MyST](https://myst-parser.readthedocs.io/en/stable/intro.html) to have the ease of writing of markdown while still being able to use advanced features of RST. 


## Consequences

* The project is set up for ease and speed of development.
* Choices are still good enough for production.
* Properly handling the project in production as well as deploying it is deferred. The dependency on CDN should be removed for privacy reasons as well as to make the CSP stricter.
* Choices that may be changed at a later point:
  * Bootstrap if I find something nice and small that isn’t a problem to set up. It will imply to rewrite all the CSS, but if changed early enough that should be manageable. Perhaps, the solution will be to just customize it.
  * Crispy form to have more control over the HTML.
* The ADRs are ready to roll as part of the project documentation!
* We depend on a very Python thing (RST and MyST) for documentation. Since they should mostly be Markdown documents, I don’t think it’s an issue.
