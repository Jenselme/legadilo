# 8 - Browser extension

* **Date:** 2024-12-01
* **Status:** Accepted

## Context

Currently, to subscribe to a feed or to save an article, I need to copy the URL of the resource and paste it in the proper form in the app.
I’ve put the *Add an article* in the navbar since it’s the one I use most often and hidden the *Subscribe to a feed* inside feed admin since I don’t do it much.
This is to avoid having too many links in the navbar.

Either way, the main pain point is that I must switch context in order to save something new.
If I have many of those actions to do, it’s quickly tiresome.

Since everything we need (link, title and content of the article) as well as potential feed links is accessible in the browser, it makes sense to have an extension that will do these actions directly on the website page.
The interaction with the solution would be much smoother.

See:
* [Crease a basic browser extension](https://github.com/Jenselme/legadilo/issues/156)
* [Improve the browser extension](https://github.com/Jenselme/legadilo/issues/321)
* [Create an API](https://github.com/Jenselme/legadilo/issues/318)


## Decisions

* Let’s build an extension.
* Since it’s quite basic and doesn’t need to intercept HTTP requests, we can go directly with manifest v3.
* We’ll put some bootstrap theming and build the base features: add an article and edit some its metadata, subscribe to a feed and edit some of its metadata.
* We will leverage our newly created API to do that.
* We want an extension for Firefox and Chromium based browsers.
* We will use bootstrap for the theme and our tags extension to provide a better UX.
  To avoid making the extension more complex, we won’t use any other libs (at least for now).


## Consequences

* The API must be adjusted in consequence (some use cases were missed in the initial design).
* Firefox isn’t fully compliant with manifest v3 yet.
  It doesn’t support the service worker as a background script.
  After some tests (which involved to duplicate the extension), I was able to merge both extension in the same code base.
* We build the `popup.html` the old school way with elements that are displayed/hidden with JS.
  It works and is a bit messy.
  If the extension becomes more complex we may need to load a JS lib like React, Vue or Svelte to control the mess.
