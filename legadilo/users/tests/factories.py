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

from collections.abc import Sequence
from typing import Any

from django.contrib.auth import get_user_model
from factory import Faker, SubFactory, post_generation
from factory.django import DjangoModelFactory

from legadilo.core.models import Timezone
from legadilo.users.models import Notification, UserSettings


class UserFactory(DjangoModelFactory):
    email = Faker("email")
    name = Faker("name")

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):
        password = extracted or Faker(
            "password",
            length=42,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        ).evaluate(None, None, extra={"locale": None})
        self.set_password(password)

    @post_generation
    def user_settings(self, create: bool, extracted: Sequence[Any]):
        if self.pk:
            timezone, _created = Timezone.objects.get_or_create(name="UTC")
            self.settings = UserSettingsFactory(user=self, timezone=timezone)

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            # Some post-generation hooks ran, and may have modified us.
            instance.save()

    class Meta:
        model = get_user_model()
        django_get_or_create = ["email"]


class UserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings


class NotificationFactory(DjangoModelFactory):
    user = SubFactory(UserFactory)

    class Meta:
        model = Notification
