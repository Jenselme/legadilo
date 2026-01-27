# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from allauth.account.signals import user_signed_up
from django.utils import translation

from legadilo.reading.models import ReadingList


def create_default_reading_list_on_user_registration(sender, user, **kwargs):
    with translation.override(user.settings.language):
        ReadingList.objects.create_default_lists(user=user)


user_signed_up.connect(create_default_reading_list_on_user_registration)
