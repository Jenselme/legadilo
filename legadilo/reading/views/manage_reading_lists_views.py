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

from http import HTTPStatus
from typing import Any

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.core.forms import FormChoices
from legadilo.core.forms.fields import MultipleTagsField
from legadilo.reading import constants
from legadilo.reading.models import ReadingList, ReadingListTag, Tag
from legadilo.users.models import User
from legadilo.users.user_types import AuthenticatedHttpRequest


@require_GET
@login_required
def reading_list_admin_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    return TemplateResponse(
        request,
        "reading/reading_lists_admin.html",
        {"reading_lists": ReadingList.objects.get_all_for_user(request.user)},
    )


class ReadingListForm(forms.ModelForm):
    tags_to_include = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_("Articles with these tags will be included in the reading list."),
    )
    tags_to_exclude = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_("Articles with these tags will be excluded from the reading list."),
    )

    def __init__(
        self,
        *,
        data=None,
        instance: ReadingList | None = None,
        initial: dict[str, Any],
        tag_choices: FormChoices,
    ):
        super().__init__(data=data, instance=instance, initial=initial)
        self.fields["tags_to_include"].choices = tag_choices  # type: ignore[attr-defined]
        self.fields["tags_to_exclude"].choices = tag_choices  # type: ignore[attr-defined]

    class Meta:
        model = ReadingList
        fields = (
            "title",
            "enable_reading_on_scroll",
            "auto_refresh_interval",
            "order",
            "read_status",
            "favorite_status",
            "for_later_status",
            "articles_max_age_value",
            "articles_max_age_unit",
            "articles_reading_time",
            "articles_reading_time_operator",
            "tags_to_include",
            "include_tag_operator",
            "tags_to_exclude",
            "exclude_tag_operator",
            "order_direction",
        )

    def save(self, commit: bool = True):  # noqa: FBT001,FBT002 Boolean-typed positional argument in function definition
        self._update_tags()

        return super().save(commit=commit)

    def create(self, user: User):
        create_data = self.cleaned_data.copy()
        # Tags are managed with a many-to-many relationship and thus must be created independently
        # and cannot be passed to .create
        create_data.pop("tags_to_include")
        create_data.pop("tags_to_exclude")
        reading_list = ReadingList.objects.create(**create_data, user=user)
        self.instance = reading_list

        self._update_tags()

        return reading_list

    def _update_tags(self):
        tags_to_include = self.cleaned_data.pop("tags_to_include")
        if tags_to_include != self.initial["tags_to_include"]:
            ReadingListTag.objects.associate_reading_list_with_tag_slugs(
                self.instance,
                tags_to_include,
                filter_type=constants.ReadingListTagFilterType.INCLUDE,
            )

        tags_to_exclude = self.cleaned_data.pop("tags_to_exclude")
        if tags_to_exclude != self.initial["tags_to_exclude"]:
            ReadingListTag.objects.associate_reading_list_with_tag_slugs(
                self.instance,
                tags_to_exclude,
                filter_type=constants.ReadingListTagFilterType.EXCLUDE,
            )


@require_http_methods(["GET", "POST"])
@login_required
@transaction.atomic()
def reading_list_create_view(
    request: AuthenticatedHttpRequest,
) -> TemplateResponse | HttpResponseRedirect:
    tag_choices = Tag.objects.get_all_choices(request.user)
    form = _build_form_from_reading_list_instance(tag_choices)
    status = HTTPStatus.OK
    if request.method == "POST":
        status, form, reading_list = _create_reading_list(request, tag_choices)
        if reading_list:
            return HttpResponseRedirect(
                reverse("reading:edit_reading_list", kwargs={"reading_list_id": reading_list.id})
            )

    return TemplateResponse(
        request, "reading/edit_reading_list.html", {"form": form}, status=status
    )


def _create_reading_list(
    request: AuthenticatedHttpRequest, tag_choices: FormChoices
) -> tuple[HTTPStatus, ReadingListForm, ReadingList | None]:
    form = _build_form_from_reading_list_instance(tag_choices, data=request.POST)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form, None

    try:
        reading_list = form.create(request.user)
    except IntegrityError:
        messages.error(
            request,
            _("A reading list with title '%s' already exists.") % form.cleaned_data["title"],
        )
        return HTTPStatus.CONFLICT, form, None

    return HTTPStatus.CREATED, form, reading_list


@require_http_methods(["GET", "POST"])
@login_required
def reading_list_edit_view(
    request: AuthenticatedHttpRequest, reading_list_id: int
) -> TemplateResponse | HttpResponseRedirect:
    reading_list = get_object_or_404(ReadingList, id=reading_list_id, user=request.user)
    tag_choices = Tag.objects.get_all_choices(request.user)
    form = _build_form_from_reading_list_instance(tag_choices, reading_list=reading_list)
    status = HTTPStatus.OK

    if request.method == "POST" and "delete" in request.POST:
        reading_list.delete()
        return HttpResponseRedirect(reverse("reading:reading_lists_admin"))

    if request.method == "POST" and "make-default" in request.POST:
        ReadingList.objects.make_default(reading_list)
        reading_list.refresh_from_db()
    elif request.method == "POST":
        form = _build_form_from_reading_list_instance(
            tag_choices, data=request.POST, reading_list=reading_list
        )
        if form.is_valid():
            form.save()
        else:
            status = HTTPStatus.BAD_REQUEST

    return TemplateResponse(
        request,
        "reading/edit_reading_list.html",
        {"reading_list": reading_list, "form": form},
        status=status,
    )


def _build_form_from_reading_list_instance(
    tag_choices: FormChoices,
    reading_list: ReadingList | None = None,
    data=None,
):
    return ReadingListForm(
        data=data,
        instance=reading_list,
        initial={
            "tags_to_include": reading_list.reading_list_tags.get_selected_values(
                constants.ReadingListTagFilterType.INCLUDE
            )
            if reading_list
            else [],
            "tags_to_exclude": reading_list.reading_list_tags.get_selected_values(
                constants.ReadingListTagFilterType.EXCLUDE
            )
            if reading_list
            else [],
        },
        tag_choices=tag_choices,
    )
