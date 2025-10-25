<!--
SPDX-FileCopyrightText: 2023-2025 Legadilo contributors

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# How import or export data?

## How to import data?

### How to load all data from TTRSS

1. Export the data in CSV using this SQL requests (adapt the user id if needed):

   ```sql
    SELECT row_number() over (),
           cat.id                                                      AS category_id,
           cat.title                                                   AS category_title,
           feeds.id                                                    AS feed_id,
           feeds.title                                                 AS feed_title,
           feeds.feed_url,
           feeds.site_url                                              AS feed_site_url,
           article.id                                                  AS article_id,
           article.title                                               AS article_title,
           article.link                                                AS article_url,
           article.content                                             AS article_content,
           'text/html'                                                 AS article_content_type,
           article.date_entered                                        AS article_date_published,
           article.date_updated                                        AS article_date_updated,
           array_to_json(string_to_array(replace(replace(article.author, ' & ', ','), ' et ', ','),
                                         ','))                         AS article_authors,
           array_to_json(string_to_array(user_entries.tag_cache, ',')) AS article_tags,
           user_entries.last_read                                      AS article_read_at,
           user_entries.marked                                         AS article_is_favorite,
           article.lang                                                AS article_lang
    FROM ttrss_entries article
             INNER JOIN ttrss_user_entries user_entries ON user_entries.ref_id = article.id
             INNER JOIN ttrss_feeds feeds ON feeds.id = user_entries.feed_id
             LEFT JOIN ttrss_feed_categories cat ON feeds.cat_id = cat.id
    WHERE user_entries.owner_uid = 1;
    ```
2. If the export is not too big (less than a megabytes), you can go to the [import/export articles page](https://www.legadilo.eu/import-export/articles/import_export/) from you profile. You can import the feeds and articles thanks to the import custom CSV feature there.
3. If the file is too big, you will have to import it with the `import_data` command using the `custom_csv` format. For instance:

   ```bash
   python manage.py import_data --user-id 1 --source-type custom_csv ttrss_data.csv
   ```

### How to load custom data

You can load a set of articles, feed categories and feeds using a CSV file and the `import_data` command with the `custom_csv` format.
The CSV must be structured like this:

```csv
"category_id","category_title","feed_id","feed_title","feed_url","feed_site_url","article_id","article_title","article_url","article_content","article_content_type","article_date_published","article_date_updated","article_authors","article_tags","article_read_at","article_is_favorite","article_lang","comments"
```

If you don’t have an info, leave it empty.
Please note that:
- To create a category, you must provide a `category_title`
- To create a feed, you must provide a `feed_url`. We will try to download the feed file and add it properly. If this fail, we will use `feed_title` to save the feed.
- To create an article, you need `article_url`.
- You can create categories, feeds and articles and associate them all by adding data to create a feed, a category and an article in the same line. If data are missing, we will just skip the corresponding entry. If an entry was already added, it will be skipped.

### How to import other kinds of data?

- You can import feeds from [the import feeds page](https://www.legadilo.eu/import-export/feeds/import/) accessible from feed admin and then upload an OPML file.
- You can import articles from Wallabag JSON format from the [import/export articles page](https://www.legadilo.eu/import-export/articles/import_export/) from your profile.

```{admonition} Note on big imports
:class: note

If you want to import big files, you will have to use the `import_data` command. Run `python manage.py import_data --help` to learn how to use it.
```

## How to export data?

### How to export feeds?

You can export your feeds and their categories in the standard OPML format directly from the [feeds admin page](https://www.legadilo.eu/feeds/).

### How to export everything (articles, feeds, categories…)?

Go to the [import/export articles page](https://www.jujens.eu/import-export/articles/import_export/) from your profile. From there, click the _Export all articles, feeds, categories and tags_ button. You will get a CSV formatted as described above to manipulate locally or import directly. All articles will be associated with their feed and tags.
