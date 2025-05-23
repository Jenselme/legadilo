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

# Generated by Django 5.0.4 on 2024-04-16 19:03

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_missing_settings_model(apps, schema_editor):
    user_settings_model = apps.get_model("users", "UserSettings")
    user_model = apps.get_model("users", "User")

    for user in user_model.objects.all():
        user_settings_model.objects.create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "default_reading_time",
                    models.PositiveIntegerField(
                        default=200,
                        help_text="Number of words you read in minutes. Used to calculate the reading time of articles.",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="usersettings",
            constraint=models.UniqueConstraint(
                models.F("user"), name="users_usersettings_unique_per_user"
            ),
        ),
        migrations.RunPython(
            create_missing_settings_model,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="usersettings",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="settings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
