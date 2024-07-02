# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
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

# Generated by Django 5.0.6 on 2024-06-30 20:56

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0004_readinglist_order_direction_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="article",
            name="reading_article_initial_source_type_valid",
        ),
        migrations.RenameField(
            model_name="article",
            old_name="initial_source_title",
            new_name="main_source_title",
        ),
        migrations.RenameField(
            model_name="article",
            old_name="initial_source_type",
            new_name="main_source_type",
        ),
        migrations.AddConstraint(
            model_name="article",
            constraint=models.CheckConstraint(
                check=models.Q(("main_source_type__in", ["FEED", "MANUAL"])),
                name="reading_article_main_source_type_valid",
            ),
        ),
    ]