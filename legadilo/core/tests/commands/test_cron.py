#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestCron:
    def test_cron(self):
        # Smoke test, must not raise.
        call_command("cron", schedule=[0])
