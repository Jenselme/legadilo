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

# Generated by Django 3.1.7 on 2021-02-04 14:49

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("sites", "0003_set_site_domain_and_name"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="site",
            options={
                "ordering": ["domain"],
                "verbose_name": "site",
                "verbose_name_plural": "sites",
            },
        ),
    ]
