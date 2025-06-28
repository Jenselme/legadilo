<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 10 - Prevent duplicated article in feeds when URL changes

* **Date:** 2025-06-10
* **Status:** Accepted

## Context

Currently, articles are considered unique by their URL only.
It’s a good thing for manually added articles, less so for articles coming from feeds.
Some feeds will republish an article with a different URL after an update.
Luckily, a feed should provide a unique and stable id to all articles in the feed.
This id should be used in `FeedArticle` to identify whether an article already exists.

I think I used the URL of the article assuming (no ADR on this sadly):
- It wouldn’t change and thus could be used as a stable identifier.
- It could have been common between feeds and manually added articles removing the need to handle a specific identifier for articles in feeds. 

This was a wrong analysis.
Cases that can happen:
- Articles are only present in one feed:
  - The article id from the feed will be used to find the article.
    If the source messes their feed and provides the same id for multiple articles, it’s not our problem but the source’s.
    Same if the source changes the URL and gives the article another ID, it’s not our problem.
- Article present in multiple feeds:
  - The article should have the same id if all the feeds are from the same source.
    We can’t detect this easily.
    The feed article id should be stored in the article external id for this.
    What I fear is ending up with feeds from different sources using the same id for different articles.
    It’s probably not valid, but still to be expected from poorly implemented feeds.
  - The same article could have different ids if the sources are different.
    Do nothing here: we can’t do anything, and it’s acceptable in this edge case to have duplication: the user subscribed to multiple feeds.
    It’s up to the user to change their subscription if needed.
- Article present in a feed and added manually.
  If the URLs are different, it will break, just like today.
  I don’t think we can do anything about it.

## Decisions

- Store the id of the article as defined in the feed in `FeedArticle`.
- If the same article is published again after a period of time, mark the article as unread.
  - It’s the republication of a previous article.
    It makes sense to display it again.
  - Let’s wait a full year before allowing this.
- If an article changes its URL in a feed, update `Article.url` considering the previous URL is not valid anymore and would redirect to the proper article.
  - Tracking all the URLs could be valuable, but too complex until we have actual problems with storing only one URL per article.

## Consequences

- Duplication should occur less often and not at all within a single feed.
- Let’s accept that the same article with different URLs from different sources can be created more than once for a user.
- If a user subscribes to multiple feeds (eg multiple feeds from *Le Monde* a French newspaper) and that the same article is present in more than one and this same article is published under different URLs, then a duplicated article will be entered.
  - It seems like a rare enough edge case to be allowed until a complaint arises.
  - I think it’s safer to assume some feeds will use a bad id scheme that could conflict between them.
    Eg, sites using merely using their integer database id as id in the feed.
