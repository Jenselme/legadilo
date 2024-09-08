# Changelog


## 24.09.1

### Breaking change

- Command `cleanup_old_updates` has been renamed into `clean_data`.
  - It still cleans up old feed updates and articles fetch errors.
  - It will also clean old articles from feeds if the _Keep articles_ option is not set to _Always_ in the configuration of the feeds.

### Other changes

- Display a count of unread notifications.
  - This makes the link more visible when a user has unread notifications.
- Correct text breaks of summary.
- Re-enable feed if we re-add a disabled feed.


## 24.08.6

- Can disable read on scroll temporarily.


## 24.08.5

- Correct display of `figcaption` element on article details.
- Correct display of big `pre` blocks on article details to prevent horizontal scrolling of the whole page.
- Prevent overflow of article details content.
- Add a link to the disabled feeds in notifications.
- Add notification creation time on notifications page.


## 24.08.4

- Allow users to enable MFA.


## 24.08.3

- Add search:
  - Can search text in the body, summary, authors and source title of articles.
  - Can filter searches by tags.
  - Can update searched articles.


## 24.08.2

- Allow users to select a TZ to view times in their profile.
  - Ask user TZ on registration.
  - Update user profile to allow users to change their TZ.
- Automatic deactivation of broken feeds is more consistent with their refresh period.
- Prevent read on scroll to be completely broken in one request of the chain failed.


## 24.08.1

- Add notifications when a feed is disabled.


## 24.07.8

- Can configure SMTP user, password and TLS connection.


## 24.07.7

- Prevent overflow of tags and pagination selector (mostly a mobile issue).


## 24.07.6

- Prevent overflow for content with very long links.


## 24.07.5

- Improve documentation.


## 24.07.4

- Correct daphne port.


## 27.07.3

Skipped because of release script bug due to local testing.


## 24.07.2

- Scroll to the top of reading lists when going back to them.
- Refresh session at every request to prevent to reconnect to often while loosing session rapidly on used devices.
- Don’t try to update the feed if we failed to fetch its file.


## 24.07.1

Initial release:
- Can subscribe to feeds.
  - Each feed is associated with tags that are used to tag the article.
  - Can select frequency of updated.
  - Invalid feeds are automatically disabled.
- Can manually add articles and tag them.
