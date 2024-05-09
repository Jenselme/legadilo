# 3 - Article deduplication

* **Date:** 2024-04-19
* **Status:** Accepted


## Context

A user can add the same article in different manner:
* Add it manually multiple times. That’s the easy part and we can mark the article as unread if that’s the case.
* Add it manually and from a feed.
* Add it indirectly through a feed and then manually.
* It can be present in multiple feeds: because the user subscribed to an atom and a RSS feed or because the same article is present in multiple feeds (this could happen on some media sites which propose multiple feed like main news, economic news…).

How could this work?
* The same article (identified by its link) must only be added once. We don’t want it to appear multiple times in a reading list since this would only create confusion.
* We would like for it to be linked to all feeds. But if it’s linked to many feeds, we don’t want to overcrowd our interface by displaying all the feeds it’s linked to.
* If it was initially added manually, we would like to know it and keep this display.


## Decision

* If the article already exists and is re-added manually, we mark it as unread and merge the tags.
* If the saved article has content but not the new one, we don’t erase the content.
* If the manually added article has content, we always save the updated content.
* If the article comes from a feed, we only update the content if it’s more recent that what we have.
* We remove the direct link between an article and a feed. An article is now linked to a user and to feeds with a many to many.
* We store in each article its initial source to display it by default. We can then display the extra sources in a tooltip on hover if we want. For this, we can:
  * Duplicate the data each time: the source type (manual or feed) and the source title (ie the title of the site or the title of the feed).
  * Since we have feed objects, we can avoid this duplication by linking an article to its feed to get this data. We can store which one is the initial feed in a foreign key.
  * For manually added articles, we could create a site table which list all sites to avoid this duplication. But since they will be much rarer and from many different sources, it’s probably not worth it.
  
  We will always save the initial source in the article. This will result in some duplication, but it’s probably manageable and won’t be an issue until we have an insane amount of articles.


## Consequences

* We preserve content if we have it.
* Previously saved content can be erased unless we develop a history system. Probably fine at least for the start.
* We break a loop between articles and feeds: now feeds depends on article so it can create them and mange its link but an article don’t directly depend on a feed any more. This will help for our app split later on.
* We will need to change our strategy to create/update articles from feed to not erase content and only update if the data is more recent.
* We have some duplication in article source title. But it should stay reasonable and will ease its usage.
