<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# 13 - Group of articles

* **Date:** 2025-06-10
* **Status:** Accepted
* **Update:** Completed by 0015-simplify-some-m2md.md

## Context

Sometimes articles are published in groups: instead of doing one very long article on a subject, an author creates a series of articles that belong together.
The goal is to be able to put all these articles in the same group to highlight this fact and allow users to more easily go from one to the next or read the full series on one page.

## Decisions

- Create an `reading.ArticleGroup` model.
  It will have these fields:
    - `created_at` and `updated_at`
    - `title`
    - `description`
    - `tags`
- Each article can be in only one group: I can’t think of any real interest of allowing each article to be in multiple groups, and I think it would create confusion since all articles in a group could have different reading statuses depending on their other groups and the order in which they were read there.
  We also already have tags to identify articles belonging to the same subject.
- Groups can be created or selected when adding an article if the form and the extension.
  They can also be created or selected from the details page of an article.
    - Using the simple select element of bootstrap 5 tags will allow the users to select the proper group.
    - New articles are added at the end of the existing group.
    - Articles in a group inherit the tags of this group.
      No other tags can be added or removed.
      To change the tags of the article, the group must be edited.
      Having a link between the article and its tags will avoid adaptations from other parts of the code (search and display mostly) and avoid some edge cases handling.
      It seems clearer and cleaner this way.
      Try to find something that works, remains simple and still allows the addition of tags to the first article of a group.
    - In the form only, propose an extra form to allow the creation of a group with its title, description, tags and multiple articles in it.
      The user can add URL fields in the form to add as many articles as possible in one go.
- Groups are not listed directly.
  Articles of a group are listed as usual following the same rules as other articles.
  They just have an extra link (a bit like articles linked to a feed) to access the group details.
  When the details page of an article linked to a group is opened:
    - Extra links are displayed: one to view the previous article of the group, one to view the next one.
    - Extra buttons are displayed: one to mark the article as read and go to the next one.
- Groups have their own details page.
    - On it, their title, tags, description and list of linked articles with their summaries and read are displayed.
    - Their title, tags, description and associated articles can be edited.
    - The order of the articles can be changed through drap & drop (or an int field if it’s too hard).
    - Users can access a full view of the group with all articles separated by `<hr>`.
      On this page, the *Mark as read* button will mark all articles of the group as read.
    - Users can also delete a group from there.
- All groups are listed in the "admin" on a dedicated page like feeds or reading lists.
    - Users can search for a group based on their title/description like what we have for feeds.
    - Users can filter read/unread groups.
        - If all articles of a group are read, then the group itself is displayed as read.
          Otherwise, the group is unread.
    - Users can access the details of a group from there.
- When deleting a group, no matter the method, the user is given the choice to delete the group but keep the articles or delete the group and its articles.

## Consequences

- It will probably require new work to improve how groups are listed and managed.
  Relying on the admin doesn’t seem to make groups easy to find.
  They seem a bit outside the application and too far from the articles.
  But it’s not obvious if they could/should be listed as articles or something else (what?).
- Opened questions:
    - Should they have a favorite status?
      If so, how should it work with the favorite status of the articles in it?
      For the initial implementation, only articles can have that.
- If we have drag and drop to reorder articles in groups, we should probably also use this to reorder reading lists.
- Since we need to store the order of the article in the group in the link between a group and its article, we need a join table between a group and its articles.
  So putting an article into multiple groups isn’t a big deal in the database point of view.
