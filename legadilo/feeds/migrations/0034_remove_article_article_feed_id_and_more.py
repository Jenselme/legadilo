# Generated by Django 5.0.4 on 2024-04-20 16:01

from django.db import migrations, models

import legadilo.utils.validators


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0033_remove_article_feeds_article_article_unique_in_feed_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="article",
            old_name="article_feed_id",
            new_name="external_article_id",
        ),
        migrations.AlterField(
            model_name="article",
            name="external_article_id",
            field=models.CharField(
                blank=True, default="", help_text="The id of the article in the its source."
            ),
        ),
        migrations.RenameField(
            model_name="article",
            old_name="feed_tags",
            new_name="external_tags",
        ),
        migrations.AlterField(
            model_name="article",
            name="external_tags",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Tags of the article from the its source",
                validators=[
                    legadilo.utils.validators.JsonSchemaValidator({
                        "items": {"type": "string"},
                        "type": "array",
                    })
                ],
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="authors",
            field=models.JSONField(
                blank=True,
                default=list,
                validators=[
                    legadilo.utils.validators.JsonSchemaValidator({
                        "items": {"type": "string"},
                        "type": "array",
                    })
                ],
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="contributors",
            field=models.JSONField(
                blank=True,
                default=list,
                validators=[
                    legadilo.utils.validators.JsonSchemaValidator({
                        "items": {"type": "string"},
                        "type": "array",
                    })
                ],
            ),
        ),
    ]