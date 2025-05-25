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
from http import HTTPStatus

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.reading.models import Tag
from legadilo.reading.models.tag import SubTagMapping
from legadilo.types import FormChoices
from legadilo.users.models import User
from legadilo.users.user_types import AuthenticatedHttpRequest
from legadilo.utils.security import full_sanitize


@require_GET
@login_required
def tags_admin_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    searched_text = full_sanitize(request.GET.get("q", ""))

    return TemplateResponse(
        request,
        "reading/tags_admin.html",
        {
            "tags": Tag.objects.list_for_admin(request.user, searched_text=searched_text),
            "searched_text": searched_text,
        },
    )


class TagForm(forms.ModelForm):
    title = forms.CharField(help_text=_("Editing the title will change the slug of the tag too!"))
    sub_tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "These tags will be automatically added to the article when this tag is selected."
        ),
    )

    def __init__(
        self, data=None, *, instance: Tag | None = None, tag_choices: FormChoices, **kwargs
    ):
        super().__init__(data, instance=instance, **kwargs)
        self.fields["sub_tags"].choices = tag_choices  # type: ignore[attr-defined]

    class Meta:
        model = Tag
        fields = ("title", "sub_tags")

    def save(self, commit: bool = True):  # noqa: FBT001,FBT002 Boolean-typed positional argument in function definition
        self._update_tags()

        return super().save(commit=commit)

    def create(self, user: User):
        tag = Tag.objects.create(
            title=self.cleaned_data["title"],
            user=user,
        )
        self.instance = tag

        self._update_tags()

        return tag

    def _update_tags(self):
        sub_tags = self.cleaned_data.pop("sub_tags")
        if sub_tags == self.initial.get("sub_tags", None):
            return

        SubTagMapping.objects.associate_tag_with_sub_tags(
            self.instance, sub_tags, clear_existing=True
        )


@require_http_methods(["GET", "POST"])
@login_required
@transaction.atomic()
def create_tag_view(request: AuthenticatedHttpRequest) -> TemplateResponse | HttpResponseRedirect:
    tag_choices = Tag.objects.get_all_choices(request.user)
    form = TagForm(tag_choices=tag_choices)
    status = HTTPStatus.OK
    if request.method == "POST":
        status, form, tag = _create_tag(request, tag_choices)
        if tag:
            return HttpResponseRedirect(reverse("reading:edit_tag", kwargs={"pk": tag.id}))

    return TemplateResponse(request, "reading/edit_tag.html", {"form": form}, status=status)


def _create_tag(
    request: AuthenticatedHttpRequest, tag_choices: FormChoices
) -> tuple[HTTPStatus, TagForm, Tag | None]:
    form = TagForm(request.POST, tag_choices=tag_choices)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form, None

    try:
        tag = form.create(request.user)
    except IntegrityError:
        messages.error(
            request, _("A tag with title '%s' already exists.") % form.cleaned_data["title"]
        )
        return HTTPStatus.CONFLICT, form, None

    return HTTPStatus.CREATED, form, tag


@require_http_methods(["GET", "POST"])
@login_required
@transaction.atomic()
def edit_tag_view(request: AuthenticatedHttpRequest, pk: int) -> HttpResponse:
    tag = get_object_or_404(Tag, pk=pk, user=request.user)

    if request.method == "POST" and "delete" in request.POST:
        tag.delete()
        target_url = reverse("reading:tags_admin")
        if not request.htmx:
            return HttpResponseRedirect(target_url)
        return HttpResponse(headers={"HX-Redirect": target_url, "HX-Push-Url": "true"})

    all_tag_choices = Tag.objects.get_all_choices(request.user)
    tag_choices = [choice for choice in all_tag_choices if choice[0] != tag.slug]
    initial_sub_tags = SubTagMapping.objects.get_selected_mappings(tag)
    form = TagForm(
        instance=tag,
        tag_choices=tag_choices,
        initial={"sub_tags": initial_sub_tags},
    )
    if request.method == "POST":
        form = TagForm(
            data=request.POST,
            instance=tag,
            tag_choices=tag_choices,
            initial={"sub_tags": initial_sub_tags},
        )
        if form.is_valid():
            form.save()

    return TemplateResponse(request, "reading/edit_tag.html", {"form": form, "tag": tag})
