<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 12 - Simplify article deletion

* **Date:** 2025-06-10
* **Status:** Accepted
* Supersedes <project:./0006-delete-articles-linked-with-feeds.md>

## Context

Deletion of articles linked to a feed still needs special care to prevent a deleted article from being re-added the next time a feed is updated.
It turns out that the provided solution with a `feeds.FeedDeletedArticle` table couples the `reading` app with the `feeds` app.
The link is isolated in its own file, but still.
It’s also weird and I even forgot to do this properly when I implemented article deletion in the API.
It also requires special care when updating the feeds.
So after having it for a while and giving it more thoughts, it appears that the solution created in [ADR 0006](project:./0006-delete-articles-linked-with-feeds.md) isn’t that good.

Potential solutions:
- Move the model in the `reading` app to at least get rid of the problematic coupling at code level.
  This would require a link at db level.
  - Pros:
    - Close to the current system.
  - Cons:
    - Not that much cleaner.
- Create a new model in the `reading` app with (`article_url`, `feed_url`) to have no direct coupling at all.
  - Pros:
    - Probably easy to do.
    - Easy to use.
  - Cons:
    - It’s weird and doesn’t look clean.
    - We’d need to use the article id from the feed.
- Add a `deleted_at` field on `reading.Article`.
  This field would be filled when an article linked to a feed is deleted by the user (other articles are deleted immediately as usual).
  The articles marked as deleted would then be effectively deleted in our clean data process if they haven’t been seen in the feeds for a while.
  If the article pops again after this delay, it’s safe to consider it again as a new article.
  The last seen date could be store in `FeedArticle` by updating the `updated_at` field each time the article is seen in the feed.
  - Pros:
    - Easy to exclude deleted articles.
  - Cons:
    - Pollutes the article model with something that is very linked to feeds.
    - Still requires a big adaptation to make sure deleted articles are never included where they must not be.
- Add a `deleted_at` field on `feeds.FeedArticle` and exclude articles with `main_source_type` set to `FEED` if any link with a feed is marked as deleted.
  After a given time has passed with the article remaining unseen, the article and its link to the feed would be deleted.
  Once again, `FeedArticle.updated_at` could be used to detect when an article was last seen in feeds.
  - Pros:
    - Deletion of feed articles is only in the feed app.
  - Cons:
    - Harder to exclude relevant articles.
    - Forced to query the link with feeds to display any articles.
- Variant of the above: add an `article_deleted_at` field on `feeds.FeedArticle` and allow the `article_id` field to be null.
  This way, articles can be deleted immediately, and when we add articles from feeds, we know whether the article has been deleted and don’t readd it without any impact on the reading app.
  - Pros:
    - Isolate this feed related behavior in the feed app.
    - No impact on the articles nor how they are fetched and displayed.
    - Can delete articles with `.delete()` and let `on_delete=models.SET_NULL` update `feeds.FeedArticle` at database level.
  - Cons:
    - We will have `FeedArticle` pointing to no article for a time.
      Probably acceptable if well documented.

See:
- [Can delete articles linked to a feed](https://github.com/Jenselme/legadilo/issues/265)
- [Simplify how article deletion is handled](https://github.com/Jenselme/legadilo/issues/427)

## Decisions

Let’s:
- Delete articles the usual way.
- `FeedArticle.last_seen_at` must still be updated for deleted articles.
  This will allow for article republication the "normal" way.
- Assume the id of the article in the feed is stable and detect deletion based on this id.

## Consequences

- Break the need to handle feed related logic when deleting an article.
- No impact on how articles are fetched.
- Dangling `feeds.FeedArticle` objects could be there a while.
  Sad, but not a true problem.
