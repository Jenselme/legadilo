# 4 - User settings

* **Date:** 2024-05-09
* **Status:** Accepted


## Context

We want each user to be able to configure the app.
At first, it will only concern the reading speed so that we can calculate the reading time.


## Decision

To avoid cluttering the default user model, we will put these settings into a dedicated `UserSettings` model.
We will link it with the `User` model with a `OneToOneField` (it doesn’t make sense to have more than one).
It’s also the solution I’ve seen recommended many times over.


## Consequences

* We need a new model and to fetch it with a join.
* We keep the `User` model clean and simple.
