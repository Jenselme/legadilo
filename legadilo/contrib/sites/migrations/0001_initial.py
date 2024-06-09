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

import django.contrib.sites.models
from django.contrib.sites.models import (
    _simple_domain_name_validator,  # noqa: PLC2701 Private name import
)
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Site",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "domain",
                    models.CharField(
                        max_length=100,
                        verbose_name="domain name",
                        validators=[_simple_domain_name_validator],
                    ),
                ),
                ("name", models.CharField(max_length=50, verbose_name="display name")),
            ],
            options={
                "ordering": ("domain",),
                "db_table": "django_site",
                "verbose_name": "site",
                "verbose_name_plural": "sites",
            },
            bases=(models.Model,),
            managers=[("objects", django.contrib.sites.models.SiteManager())],
        ),
    ]
