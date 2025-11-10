# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from crispy_forms.helper import FormHelper
from django.forms import BaseForm, BaseFormSet


class BaseInlineTableFormSet[T: BaseForm](BaseFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.template = "bootstrap5/table_inline_formset.html"
        self.helper.form_tag = False
