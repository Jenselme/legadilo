# 1 - Organizing articles

* **Date:** 2024-03-17
* **Status:** Accepted

## Context

We will gather many articles:
* From feeds
* From direct addition of the users.

All of them must be organized so that we can find them quickly.

Since we can also have lots of feeds, we must also be able to group them.
This is done traditionally in categories.


## Decision

To give the user as much flexibility as possible:
* It must be possible to add or remove any tags to any articles. If we try to tag an article with a tag that doesn’t exist, it’s created automatically.
* When you try to add a tag, you must be able to see the list of existing tag and search through them. This search must ignore case and accentuation.
* If a tag is not associated to anything, it must not be deleted automatically.

For articles that are coming from feeds, we must allow them to be tagged with a set of default tags.
We will list them on the detail page of a feed.
Just like with articles: we can select a tag with autocomplete and create new ones on the fly.
This will also help us to organize the feeds.

If we change this list of tags, we must be able to retag all existing articles.


## Consequences

* We don't rely (at least not yet) on the tags that may come directly from the feed: this feature doesn't seem used and implementing it correctly is not that easy (we must be able to delete and remap these tags to those we have in the system).
* To avoid lots of page reload, we will rely on HTMX to enhance our HTML.
* We will need a select with autocomplete (not available by default in bootstrap).
* We don’t need an extra concept to organize feeds. This may be an issue when we will try to export into a standard format. But that’s for much later.
