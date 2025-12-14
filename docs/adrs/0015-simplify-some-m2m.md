<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 15 - Simplify some many to many relations

* **Date:** 2025-12-05
* **Status:** Accepted
* **Update:** 0013-group-of-articles.md

## Context

Some M2M relations are very complex and introduce a lot of unwanted complexity:

* Articles can be linked to multiple feeds.
  While this won’t change for technical reason, finding the main feed (ie the feed for which the article was first added) for which we want to display the feed title is harder and requires PG specific aggregation for display and for export.
* Links between articles and tags keep the tagging reason to avoid retagging an article with a manually deleted link.
  This introduces lots of weirdness when querying for tags to exclude them.
* An article can only be in one group, but the link is handled in a many-to-many to store the order within the group.
  This makes finding the group of the articles harder.

This is also a problem if we want to support multiple database backends: the more complex the queries, the harder it will be.
Getting rid of PG specific aggregation is required and too complex with the current implementation.

## Decision

* Keep articles linked to multiple feeds but also link them to their main feed on creation.
* Remove the tagging reason. If a user untags an article, the link is deleted.
  To prevent unwanted side effects, tag articles automatically *only* when the articles are created.
  Tags for existing articles must always be edited manually by the user.
* Link articles directly to a group.

## Consequences

* It’s easier to display and export an article linked to a feed.
* Queries to get tags of an article are simpler, and we have a saner behavior by not updating manually changed articles automatically.
  If the list of tags of a feed is updated, only new articles will be tagged automatically.
  Existing ones can be updated thanks to the search actions.
  It’s a bit more cumbersome, but rare enough to be worth it, in my opinion.
* It’s easier to get the group of articles and thus to display it in the UI.
  I find it a bit sad to have the group order in the article model, but it’s acceptable given the simplicity gains.
