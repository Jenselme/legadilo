# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.core.utils.types import FormChoices
from legadilo.feeds.models import Feed, FeedCategory, FeedTag
from legadilo.users.user_types import AuthenticatedHttpRequest

from ...core.forms.fields import MultipleTagsField
from ...reading.models import Tag
from .. import constants


@require_GET
@login_required
def feeds_admin_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    searched_text = request.GET.get("q", "")

    return TemplateResponse(
        request,
        "feeds/feeds_admin.html",
        {
            "searched_text": searched_text,
            "feeds_by_categories": Feed.objects.get_by_categories(
                request.user, searched_text=searched_text
            ),
            "breadcrumbs": [
                (reverse("feeds:feeds_admin"), _("Feeds admin")),
            ],
        },
    )


class EditFeedForm(forms.ModelForm):
    feed_url = forms.URLField(label=_("Feed URL"), assume_scheme="https", disabled=True)
    site_url = forms.URLField(label=_("Site URL"), assume_scheme="https", disabled=True)
    refresh_delay = forms.ChoiceField(
        label=_("Refresh delay"),
        required=True,
        choices=constants.FeedRefreshDelays.choices,
        initial=constants.FeedRefreshDelays.DAILY_AT_NOON,
    )
    article_retention_time = forms.IntegerField(
        label=_("Article retention period"),
        required=True,
        min_value=0,
        help_text=_(
            "Define for how long in days to keep read articles associated with this feed. Use 0 to "
            "always keep the articles."
        ),
    )
    open_original_url_by_default = forms.BooleanField(
        label=_("Open original by default"), required=False
    )
    category = forms.ChoiceField(
        label=_("Category"),
        required=False,
        help_text=_("The category of the feed to help you keep them organized."),
    )
    tags = MultipleTagsField(
        label=_("Tags"),
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
        fields = (
            "feed_url",
            "site_url",
            "refresh_delay",
            "article_retention_time",
            "open_original_url_by_default",
            "category",
            "tags",
        )

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
    feed = get_object_or_404(
        Feed.objects.get_queryset().select_related("category", "user").prefetch_related("tags"),
        id=feed_id,
        user=request.user,
    )
    tag_choices = Tag.objects.get_all_choices(request.user)
    category_choices = FeedCategory.objects.get_all_choices(request.user)
    form = _build_form_from_feed_instance(feed, tag_choices, category_choices)
    status = HTTPStatus.OK

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
        status = HTTPStatus.BAD_REQUEST
        if form.is_valid():
            status = HTTPStatus.OK
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
            "breadcrumbs": [
                (reverse("feeds:feeds_admin"), _("Feeds admin")),
                (reverse("feeds:edit_feed", kwargs={"feed_id": feed.id}), _("Edit feed")),
            ],
        },
        status=status,
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
