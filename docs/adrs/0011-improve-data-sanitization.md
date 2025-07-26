<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 11 - Improve data sanitization

* **Date:** 2025-06-10
* **Status:** Accepted

## Context

When an article is added with RSS, the form or the API, its title, tags, summary and content are sanitized.

Safe HTML elements (as defined in `legadilo.utils.security.DEFAULT_ALLOWED_ATTRIBUTES`) and some of their attributes are allowed in the summary and the content.
They cannot be edited directly by the user: the article must be updated either with an automatic feed update or by the user by adding an article manually or refreshing the content directly.
In both cases, the data is sanitized again.
When rendering an article card or the details, these fields are marked as safe with the `|safe` template filter to allow Django to render their HTML without escaping.
This is the intended behavior since we want to preserve some markup (for paragraph, emphasis, code, quotes…).
And since the users cannot edit it, they cannot insert dangerous tags.
So, for article summary and content, we already have the intended *and* safe behavior.

In tags and titles, no HTML is allowed.
All HTML markup is removed and HTML entities like the ampersand (`&`) or chevrons (`<` and `>`) are escaped when articles as added from a feed or manually.
Both fields can be edited by users on an article details page: to add/remove tags or change the title.
Since they can contain escaped characters, they are also marked with `|safe` to render correctly.
This, for instance, allows for `Python & Django`, encoded and saved as `Python &amp; Django` in the database to be rendered as `Python & Django` in the app.
Otherwise, instead of displaying `Python & Django` as expected, `Python &amp; Django` would be displayed to the users.
Sadly, this has two side effects, one confusing and one dangerous:
- On the editing input, the title is rendered with these escaped characters (ie like this `Python &amp; Django`).
  This can be confusing for non-technical users.
- There is currently no sanitization done *at all* on what the users enter.
  So, they can enter HTML which could break display or introduce dangerous HTML tags.
  It’s not yet a huge problem *yet* since articles are not shared across users (so an attacker can only attack themselves), and the few active users we have are friends who behave nicely.
  It’s still a problem we must address *soon* since it comes with a security risk.

Potential solutions:
- Run a full sanitization on the input text with `full_sanitize` like we do with the initial input data to strip all HTML.
  Data must still be rendered with `|safe` due to the presence of escaped characters in the output.
  - Pros:
    - Straightforward.
    - Safe.
    - Doesn’t re-encode already encoded entities: so `&amp;` in the input will remain encoded as `&amp;`.
  - Cons:
    - Removes data: a user may enter "HTML data" as part of the title, ie have a valid title like `How to use <br> in HTML?`.
      With this method, this data would be removed.
      Our example would become `How to use in HTML?`.
- Escape everything the users enter with `nh3.clean_text`.
  This would mean that data would be stored with escaped entities in the database and title and tags must be marked with `|safe` to render correctly.
  This can be eased with the creation of custom form fields to handle the escaping/unescaping automatically.  
  - Pros:
    - Data is properly encoded even in the database.
      Nothing to worry about regarding the display.
  - Cons:
    - Requires extra care to prevent double escaping.
      By default, a `&amp;` present in the input would be saved as `&amp;amp;`
      With `nh3.clean_text`, even spaces would be encoded as `&#32`.
      It would mean that data must be decoded before being displayed in the input and the user makes any edit.
    - Data in the database is hard to read and edit.
      This only impacts instance administrators with Django admin for debugging purposes, so not something to be concerned about.
- Save the raw text supplied by the user (with potentially dangerous tags) and let Django escape the content when an article is rendered.
  - This implies to:
    - Remove our `|safe` template tags for titles and tags.
    - Unescape entities as part of `full_sanitize` to have HTML entities correctly displayed in the Django templates.
  - Pros:
    - Seems like a more standard way to handle these cases.
      Contents of text inputs are not interpreted as HTML, so no danger on that side (and Django would escape it if needed anyway).
    - Most of the work will be handled by the normal flow of using Django.
    - Less need on `|safe` making valid usage easier to spot and audit!
  - Cons:
    - Potentially unsafe data in the database.
      Since it will *always* be displayed by a safe templating engine, this should be a big deal.
      Even if an app is made, modern JS frameworks also escape HTML entities correctly by default nowadays.

Note:
Users can also enter comments on an article.
A full sanitization is already done the text input.
Since once again, users may legitimately include HTML content, this doesn’t seem like a good solution since it can cause data losses.

See also:
- [Better sanitize form data](https://github.com/Jenselme/legadilo/issues/327)

### Code samples

The widget to display the values with `|safe` to display them as the users expect:
```python
class SafeValueTextInput(widgets.TextInput):
    def format_value(self, value):
        value = super().format_value(value)
        if value:
            value = html.unescape(value)
        return value
```

The field that will clean the text:
```python
class CleanedCharField(forms.CharField):
    widget = SafeValueTextInput

    def clean(self, value):
        if value:
            value = value.strip()
            value = nh3.clean_text(value)
        return super().clean(value)
```

## Decisions

Let’s store raw user data and let Django sanitize at display.
It’s standard, safe and simple to implement.

Actions to solve the problem:
1. Unescape HTML entities at the end of `full_sanitize` to store them as is and prevent double escaping in the templates.
2. Rerun the proper sanitization on all articles titles dans tags like this to make sure existing data will never be a problem:
   1. Unescape what is saved to avoid double escaping.
   2. Run the new `full_sanitize`.
3. Remove the `|safe` template tag when displaying titles and tags.
4. Remove the usage of `mark_safe`.
   It’s currently used to render the title of the article or the feed and provide a link to them when they are added.
   Rely on the template instead.
5. Don’t sanitize the text entered by the user in the comment textarea, *but* sanitize the output of the rendering as Markdown with `sanitize_keep_safe_tags`.
6. Make sure tags can be transformed to slug no matter how they are created.

## Consequences

- We’ll have something safer than what we have now.
- No data loss and users can enter HTML code that won’t be interpreted in titles, tags and comments.
- The solution is straightforward and standard.
- Reduces the reliance of escape hatches like `|safe` to render data, making places where it’s necessary easier to find and audit.
