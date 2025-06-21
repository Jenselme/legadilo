<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 6 - Delete articles linked with feeds

* **Date:** 2024-10-12
* **Status:** Accepted

## Context

We can delete articles that were never linked to a feed easily: we just have to delete the row from the database and the article is gone until the user adds it again manually.
For feeds, it’s different: if we delete the row from the database, it will come back the next time we fetch the feed as a new article (that is until the article is removed from the feed).
That’s not the behavior we want.

We could scrap the content of article and have a `DELETED` status.
However, it would be hard to maintain and we would have to rewrite our queries to always exclude them.

The best solution would be to maintain a list of deleted articles for each feed.
This way, when we update the feed, we know which articles we must ignore.


## Decisions

* Introduce a new model `FeedDeletedArticle` that maintains a mapping of feeds to their deleted article links.
* When we delete an article *no matter the way* (manually deletion or automatic cleanup), if the article is linked to a feed, we add an entry to this table and only then delete the article. This will solve two bugs:
  * We cleaned up old feed articles but had no way to know whether the article was still in the feed or not.
  * If an article was part of a feed and then was manually re-added, its source would change and would allow manual deletion. Since it was also part of a feed, the article could come back.
* Store ignored links in `FeedUpdate` to ease debugging.


## Consequences

* We can now correctly delete an article no matter how it was added.
* This table could grow and may need cleanup. We will see *later* if it’s a real problem.
* The user can still manually add the article if they so wish. So no need to prevent deletion by anything more than a modal.
