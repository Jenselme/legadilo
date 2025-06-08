# Changelog

## Unreleased

- Refresh the reading list near HH:00 The goal is to refresh the reading list closer to when the feeds where updated.
- Hide the "Make default" button when creating a reading list.
- Search improvements:
  - Can search without a search text. This enables the usage of other fields without the need to find a text to search for.
  - Can search for articles linked to specific feeds.
  - Can search articles with some external tags.
  - Can go to the advanced search page from all lists of articles pages. This allows users to start a search from a reading list, a feed page…
- Correct access to automatically generated API documentation.

## 25.05.2

- Correct search of `EmailAddress` in the Django admin.
- Browser extension:
  - Correct refresh of the access token.

## 25.05.1

- Can configure how `gunicorn` is run.
- Correctly refresh feeds configured to run on a precise day of the month.
- Delete accounts without any verified emails after a default retention period.
- Try to improve action buttons order to make order more consistent and the buttons easier to find and use.
- Can edit "open original URL by default" checkbox in admin.
- Browser extension:
  - Can save YouTube videos.
  - Can save any big HTML pages without triggering an error in the API.
  - Can save a page even when the reader mode is enabled in Firefox. It already worked correctly in Chromium-based browsers.

## 25.04.3

- Fix bugs in browser extension:
  - Correctly build more relative URLs.
  - Handle errors when listing enabled feeds and articles.

## 25.04.2

- Show reading list title and reading list actions when scrolling up.
- Improve browser extension:
  - Display site title instead of nothing for feed links without a title attribute.
  - Can go back to list of actions from error, article & feed.
  - Can delete article from extension.
  - Display on actions chooser whether the sure is subscribed feeds.
  - Display on actions chooser whether the article is already saved.
  - Can delete and disable/enable a feed from the extension.
- API changes:
  - Switch from `link` to `url` to save articles. This is done to have a consistent naming in the codebase.
  - Can list articles and filter them by URLs.
  - Can list feeds and filter them by feed URLs and enabled status.
- Correct Django admin styling.
  - This was caused by the update to `django-csp` 4.0 which changed how CSP rules are computed. It caused the admin to be unable to load its script files and stylesheets.
- Allow base64 encoded images.
- Keep h1 titles when we have more than 1.
  - Some invalid articles may have multiple h1, keep them in this case since they are "normal" article titles and thus must be kept.

## 25.04.1

- Remove async functions to simplify the code.
  - We now run with `gunicorn` instead of `daphne` in production. We use 4 `gunicorn` workers.
- Switch to Python 3.13
- Correct title for feeds without sections in feeds admin.

## 25.03.2

- Improve user Django admin page.
- Prevent errors with empty slugs.

## 25.03.1

- Can filter tags in tags admin.
- Enable tags hierarchy when updating an article on the details page.

## 25.01.1

- Correct footer background on dark mode.
- Prevent articles to be read on scroll before initial scroll to top on page load.
- Force re-authentication before managing tokens.
- Allow users to change their passwords.
- Browser extension:
  - Ask before resetting options.
  - Can open articles and feeds details.
  - Prevent extension popup to become too wide.
  - Can test the options on the settings page.
  - Support tag hierarchy.

## 24.12.6

- Can change CSP for tracking script

## 24.12.5

- Add link to changelog in footer.
- Improve existing links in footer.
- Allow you to add a custom script.
- Can fetch feed without an explicit full site URL.
- Can force feeds to refresh in the admin.
- Can refresh a reading list no mobile easily, without going to the top of the page or opening the reading list selector.
- Switch to [`uv`](docs.astral.sh/uv/) to manage dependencies.

## 24.12.4

- Use the theme (light or dark) that matches the system theme.
- Add a theme selector.
- Use a switch to enable/disable read on scroll. This is more visible and is clearer than what we had before.
- Don’t disable feeds when saving modifications with enter.
- Prevent a display issue when linking new email addresses.

## 24.12.3

- Small adjustments for extensions.
- Add a privacy policy page.

## 24.12.2

- Add a privacy policy to release the extension on Chrome webstore.
- Improve extensions to publish on Chrome & Mozilla webstore.

## 24.12.1

- Reduced allow times in which daily updates are run. We still support bi-hourly cron runs.
- Display a contact email to all authenticated users.
- Add an API:
  - The documentation is available at `/api/docs/`.
  - You can manage application tokens in your profile.
  - You can get auth tokens from these applications tokens to use the API.
- Prevent 500 errors on duplicated tags (in tag admin), feed categories and reading lists.
- Add debug information to feed admin.
- Add link to feed admin on feed articles list.
- Can search for feeds in feed admin.
- Add a browser extension.

## 24.10.3

- Correct display of titles with HTML entities when adding an article.
- Build a tag hierarchy to automatically add other tags when we select a tag.
  - The hierarchy can be edited in the tag admin.
  - Tag can also be renamed now.
- Correct the modal used when deleting feeds, feed categories and reading lists.
- Create a `cron` command run by a `cron` container by default.
  - This should ease running the CRON commands requires to update feeds (and run some cleanups) more easily within docker compose.
- Use the feed as page title when editing a feed.
- Can update feeds on saturdays and on sundays.
  - It’s to have articles updated at the start of the weekend!
- Can sort search results by relevancy & various dates.
- Can add comments on articles.
  - Text supports Markdown markup.

## 24.10.2

- Increase session lifetime to 2 weeks: it seems like a better compromise to only be disconnected if we haven’t used legadilo in a while.
- Update table of content when re-fetching an artile.
- Improve display of notifications:
  - Put unread first.
  - Hide read notifications after 3 months.
- Can delete articles linked to feeds.
- Always reload the page when going back to the reading list from article details.
  - This is to make read on scroll work. Otherwise, we will have a HTMX page change and the JS script won’t even be loaded on the page.
- Group updates for read on scroll.
  - Instead of updating articles one by one, we now mark all scrolled articles as read in one go. This should make read on scroll feel easier to use.
- Allow to use all version of PG above 16.
  - We still rely on 16 but don’t block users who would want to use 17 or above.
    - We keep 16 in our container and don’t have a way to upgrade yet anyway. See https://github.com/Jenselme/legadilo/issues/276
  - We don’t support versions below that: we developed and tested against 16 and don’t want to test other ones.
    - Future versions should work fine directly from our experience.
    - Older ones probably too given the feature set we use. But we don’t want to have any weird surprises.

## 24.10.1

- Correct `theme_color` in `manifest.json`.
- Set main source on invalid articles.
- Correct default timeout when fetching articles and RSS data.
  - They are now configurable.
  - We have a shorter timeout when fetching an article to hit the code timeout before hitting the nginx timeout configured on the default instance.

## 24.09.3

- Can subscribe with channel or playlist link.
  - For channels, it must be a link of the form `/channel/<CHANNEL_ID>`. The clean url with `/@ChannelName` doesn’t work.

## 24.09.2

- Improve logging for `clean_data`


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
- Correct article author in page metadata.
- Display a navigable table of content on the side of article details.


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
