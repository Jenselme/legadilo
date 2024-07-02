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

from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.feeds.models import Feed, FeedCategory, FeedTag
from legadilo.users.typing import AuthenticatedHttpRequest

from ...core.forms import FormChoices
from ...core.forms.fields import MultipleTagsField
from ...reading.models import Tag
from ...users.models import User
from .. import constants


@require_GET
@login_required
def feeds_admin_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    return TemplateResponse(
        request,
        "feeds/feeds_admin.html",
        {
            "feeds_by_categories": Feed.objects.get_by_categories(request.user),
        },
    )


class EditFeedForm(forms.ModelForm):
    feed_url = forms.URLField(
        assume_scheme="https",
        disabled=True,
    )
    site_url = forms.URLField(assume_scheme="https", disabled=True)
    refresh_delay = forms.ChoiceField(
        required=True,
        choices=constants.FeedRefreshDelays.choices,
        initial=constants.FeedRefreshDelays.DAILY_AT_NOON,
    )
    category = forms.ChoiceField(
        required=False,
        help_text=_("The category of the feed to help you keep them organized."),
    )
    tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to articles of this feed. To create a new tag, type and press "
            "enter. Editing this tag list will update the tags of all articles of this feed."
        ),
    )

    def __init__(
        self,
        data=None,
        *,
        instance: Feed,
        tag_choices: FormChoices,
        category_choices: FormChoices,
        **kwargs,
    ):
        super().__init__(data, instance=instance, **kwargs)
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]
        self.fields["category"].choices = category_choices  # type: ignore[attr-defined]

    class Meta:
        model = Feed
        fields = ("feed_url", "site_url", "refresh_delay", "category", "tags")

    def clean_category(self):
        if not self.cleaned_data["category"]:
            return None

        return FeedCategory.objects.get(user=self.instance.user, slug=self.cleaned_data["category"])

    def save(self, commit: bool = True):  # noqa: FBT001,FBT002 Boolean-typed positional argument in function definition
        if self.cleaned_data["tags"] != self.initial["tags"]:
            FeedTag.objects.associate_feed_with_tag_slugs(
                self.instance, self.cleaned_data["tags"], clear_existing=True
            )

        if self.cleaned_data["category"] != self.instance.category:
            self.instance.category = self.cleaned_data["category"]

        return super().save(commit=commit)


@require_http_methods(["GET", "POST"])
@login_required
def edit_feed_view(
    request: AuthenticatedHttpRequest, feed_id: int
) -> TemplateResponse | HttpResponseRedirect:
    feed = _get_feed(request.user, feed_id)
    tag_choices = Tag.objects.get_all_choices(request.user)
    category_choices = FeedCategory.objects.get_all_choices(request.user)
    form = _build_form_from_feed_instance(feed, tag_choices, category_choices)

    if request.method == "POST" and "delete" in request.POST:
        feed.delete()
        return HttpResponseRedirect(reverse("feeds:feeds_admin"))

    if request.method == "POST" and "disable" in request.POST:
        feed.disable(reason=_("Manually disabled"))
        feed.save()
        form = _build_form_from_feed_instance(feed, tag_choices, category_choices)
    elif request.method == "POST" and "enable" in request.POST:
        feed.enable()
        feed.save()
        form = _build_form_from_feed_instance(feed, tag_choices, category_choices)
    elif request.method == "POST":
        form = _build_form_from_feed_instance(
            feed, tag_choices, category_choices, data=request.POST
        )
        if form.is_valid():
            form.save()
            # Update the list of tag choices. We may have created some new one.
            tag_choices = Tag.objects.get_all_choices(request.user)
            form = _build_form_from_feed_instance(feed, tag_choices, category_choices)

    return TemplateResponse(
        request,
        "feeds/edit_feed.html",
        {
            "feed": feed,
            "form": form,
        },
    )


def _get_feed(user: User, feed_id: int) -> Feed:
    return get_object_or_404(
        Feed.objects.get_queryset().select_related("category", "user").prefetch_related("tags"),
        id=feed_id,
        user=user,
    )


def _build_form_from_feed_instance(
    feed: Feed,
    tag_choices: FormChoices,
    category_choices: FormChoices,
    data=None,
) -> EditFeedForm:
    return EditFeedForm(
        data,
        initial={
            "category": feed.category.slug if feed.category else "",
            "tags": feed.feed_tags.get_selected_values(),
        },
        instance=feed,
        tag_choices=tag_choices,
        category_choices=category_choices,
    )
