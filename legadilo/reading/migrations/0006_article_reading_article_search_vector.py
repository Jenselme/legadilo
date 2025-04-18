# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Generated by Django 5.1 on 2024-08-11 10:30

import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0005_remove_article_reading_article_initial_source_type_valid_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name="article",
            index=django.contrib.postgres.indexes.GinIndex(
                django.contrib.postgres.search.CombinedSearchVector(
                    django.contrib.postgres.search.CombinedSearchVector(
                        django.contrib.postgres.search.CombinedSearchVector(
                            django.contrib.postgres.search.CombinedSearchVector(
                                django.contrib.postgres.search.SearchVector(
                                    "title", config="english", weight="A"
                                ),
                                "||",
                                django.contrib.postgres.search.SearchVector(
                                    "summary", config="english", weight="B"
                                ),
                                django.contrib.postgres.search.SearchConfig("english"),
                            ),
                            "||",
                            django.contrib.postgres.search.SearchVector(
                                "content", config="english", weight="C"
                            ),
                            django.contrib.postgres.search.SearchConfig("english"),
                        ),
                        "||",
                        django.contrib.postgres.search.SearchVector(
                            "authors", config="english", weight="C"
                        ),
                        django.contrib.postgres.search.SearchConfig("english"),
                    ),
                    "||",
                    django.contrib.postgres.search.SearchVector(
                        "main_source_title", config="english", weight="D"
                    ),
                    django.contrib.postgres.search.SearchConfig("english"),
                ),
                name="reading_article_search_vector",
            ),
        ),
    ]
