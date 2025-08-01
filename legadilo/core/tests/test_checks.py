# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from types import SimpleNamespace
from unittest import mock

from django.db import models
from django.test import SimpleTestCase, override_settings
from django.test.utils import isolate_apps

from ..checks import check_dev_mode, check_model_names


def mock_dev_mode(value):
    return mock.patch.object(
        sys,
        "flags",
        SimpleNamespace(dev_mode=value),
    )


class CheckDevModeTests:
    def test_success_dev_mode(self):
        with override_settings(DEBUG=True), mock_dev_mode(True):
            result = check_dev_mode()
            assert result == []

    def test_success_not_debug(self):
        with override_settings(DEBUG=False), mock_dev_mode(False):
            result = check_dev_mode()
            assert result == []

    def test_fail_not_dev_mode(self):
        with override_settings(DEBUG=True), mock_dev_mode(False):
            result = check_dev_mode()
            assert len(result) == 1
            assert result[0].id == "legadilo.W001"


@isolate_apps("legadilo.core", attr_name="apps")
class CheckModelNamesTests(SimpleTestCase):
    def test_success(self):
        class Single(models.Model):  # noqa: DJ008
            pass

        result = check_model_names(
            app_configs=self.apps.get_app_configs(),  # type: ignore[attr-defined]
        )
        assert result == []

    def test_fail(self):
        class Plurals(models.Model):  # noqa: DJ008
            pass

        result = check_model_names(
            app_configs=self.apps.get_app_configs(),  # type: ignore[attr-defined]
        )
        assert len(result) == 1
        assert result[0].id == "legadilo.E001"
        assert result[0].hint == (
            "Rename to the singular form, e.g. “Plural”, or mark the name"
            " as allowed by adding 'Plurals' to"
            " legadilo.core.checks.SAFE_MODEL_NAMES."
        )
        assert result[0].obj == Plurals

    def test_success_allowed_plural(self):
        class Plurals(models.Model):  # noqa: DJ008
            pass

        mock_safe_names = mock.patch(
            "legadilo.core.checks.SAFE_MODEL_NAMES",
            new={"Plurals"},
        )

        with mock_safe_names:
            result = check_model_names(
                app_configs=self.apps.get_app_configs(),  # type: ignore[attr-defined]
            )
        assert result == []
