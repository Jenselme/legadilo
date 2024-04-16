# Generated by Django 5.0.4 on 2024-04-16 19:51
import string

from django.db import migrations, models

from legadilo.utils.security import full_sanitize


def set_initial_reading_time(apps, schema_editor):
    user_model = apps.get_model("users", "User")
    article_model = apps.get_model("feeds", "Article")

    for user in user_model.objects.all():
        for article in article_model.objects.filter(feed__user=user):
            article.reading_time = (
                _get_nb_words(article.content) // user.settings.default_reading_time
            )
            article.save()


def _get_nb_words(content: str) -> int:
    raw_content = full_sanitize(content)
    nb_words = 0
    for word in raw_content.split():
        if word.strip(string.punctuation):
            nb_words += 1

    return nb_words


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0024_readinglist_for_later_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="reading_time",
            field=models.PositiveIntegerField(
                default=0,
                help_text="How much time in minutes is needed to read this article. If not specified, it will be calculated automatically from content length. If we don't  have content, we will use 0.",
            ),
        ),
        migrations.RunPython(set_initial_reading_time, reverse_code=migrations.RunPython.noop),
    ]