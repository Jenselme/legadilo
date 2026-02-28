# 16 - Multiple database backends

* **Date:** 2026-02-28
* **Status:** Accepted


## Context

To ease self-hosting, we should support SQLite:
* it’s easier to setup even outside containers. Running a Python app isn’t that hard.
* it doesn’t include complex updates within container setup like PG does (major version updates are a pain).
* reduces the resources needed to self host the project.

It would also make development easier and consume fewer resources by reducing the number of containers needed.
When developing locally, no containers would even be needed most of the time.
`mailpit` would only be needed for email workflows and `postgres` only to check behaviors on it like advanced search.
Choosing which containers to start can be made with profiles. 

See https://github.com/Jenselme/legadilo/issues/150

## Decision

* Add support for sqlite.
* Adding support for MySQL/MariaDb should be possible at a small cost. I don’t think it’s necessary right now, and it requires a bit more work I’m not willing to do (I failed to make it directly in a standalone container, and it requires extra dependencies).

## Consequences

* Some features like search required work to function on sqlite, and some advanced search features aren’t available. Fine in most cases.
* Some tests are more complex and need to handle PG and sqlite differently (mostly for error messages).
* Migrations have to be reset to ease the transition and applying PG specific ones for search and collation.
* MySQL/MariaDb support might be added later if asked about.
