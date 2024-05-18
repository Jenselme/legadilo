# How to

## How to load all data from TTRSS

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
           article.link                                                AS article_link,
           article.content                                             AS article_content,
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

2. Import the data with the `import_data` command using the `custom_csv` format. For instance:

   ```bash
   python manage.py import_data --user-id 1 --source-type custom_csv ttrss_data.csv
   ```


## How to load custom data

You can load a set of articles, feed categories and feeds using a CSV file and the `import_data` command with the `custom_csv` format.
The CSV must be structured like this:

```csv
"category_id","category_title","feed_id","feed_title","feed_url","feed_site_url","article_id","article_title","article_link","article_content","article_date_published","article_date_updated","article_authors","article_tags","article_read_at","article_is_favorite","article_lang"
```


If you don’t have an info, leave it empty.
Please note that:
- To create a category, you must provide a `category_title`
- To create a feed, you must provide a `feed_url`. We will try to download the feed file and add it properly. If this fail, we will use `feed_title` to save the feed.
- To create an article, you need `article_link`.
- You can create categories, feeds and articles and associate them all by adding data to create a feed, a category and an article in the same line. If data are missing, we will just skip the corresponding entry. If an entry was already added, it will be skipped.
