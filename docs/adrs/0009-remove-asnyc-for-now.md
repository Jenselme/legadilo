# 9 - Remove async for now

* **Date:** 2025-04-01
* **Status:** Accepted
* Partially supersedes <project:./0000-project-setup.md> and <project:./0005-deployment.md>

## Context

After using async, it brings complexity for performance improvements we need yet.
The main issue being that we cannot yet use transactions in an async context (see [this issue](https://code.djangoproject.com/ticket/33882)).
This results in extra complexities with usages of `sync_to_async` and `async_to_sync` to switch from one context to another.

Since we do multiple database operations, I think transaction must be used to always be in a valid state.
Or to state it differently: since we are far from performance problems yet, it’s best to just use transactions for consistency than to remove them to have cleaner async support or have the complexity that comes with sync to async conversions.

Since we do lots of async requests, I still think async makes sense.
Just not now.


## Decisions

Simply the code as much as we can and remove async support for now.
It will impact many files, but it should be relatively straightforward.


## Consequences

- We may have to re-add async later on.
- Lots of code changes.
- Must have an export command to export big files.
- Use `gunicorn` to run the application in production:
  - It’s kind of a default choice for this, and I’ve used it in the past with great success. 
  - Create an incoming HTTP request timeout. Set it to 60s to allow for slow search.
  - Use 4 workers: from my experience, it’s a good number.
- We may need to allow for incoming request timeout and number of workers to be configured.
