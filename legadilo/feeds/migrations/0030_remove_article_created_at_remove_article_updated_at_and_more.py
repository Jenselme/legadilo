# Generated by Django 5.0.4 on 2024-04-20 14:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0029_article_opened_at_article_read_at_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="article",
            old_name="created_at",
            new_name="obj_created_at",
        ),
        migrations.RenameField(
            model_name="article",
            old_name="updated_at",
            new_name="obj_updated_at",
        ),
        migrations.AlterField(
            model_name="article",
            name="obj_created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                help_text="Technical date for the creation of the article in our database.",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="obj_updated_at",
            field=models.DateTimeField(
                auto_now=True,
                help_text="Technical date for the last update of the article in our database.",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="updated_at",
            field=models.DateTimeField(
                blank=True, help_text="The last time the article was updated.", null=True
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="published_at",
            field=models.DateTimeField(
                blank=True, help_text="The date of publication of the article.", null=True
            ),
        ),
    ]