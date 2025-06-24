<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 2 - Reading lists

* **Date:** 2024-03-17
* **Status:** Accepted

## Context

Users will have many articles of different sources, different types, different reading time, different subjects…
The idea is to give each user a way to define reading lists, so they can read what they want to read when they want to read it.


## Decision

All users must be able to manage their reading lists (ie create and delete them).
These list will have a name and from this name we will be able to generate a nice slug to use in URLs.

When an account is created, the following default reading list are created:
* All articles.
* Unread articles.
* Recently added.
* Favorite articles.
* All read articles.

On a longer term, we should also be able to create these lists directly from a search.


## Consequences

* We don’t need tags for the default reading lists (so we start implementing this before having to organize articles).
* The system will be flexible. We will need a good UI to ease creation and edition.
* We will also need to make sure we can find articles in a list fast. We may need to add relevant indexes or to associate each articles with its list. But that’s a decision for later when we will have articles and a clearer idea of how we use the system.
