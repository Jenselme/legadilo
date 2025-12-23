# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
from dataclasses import dataclass
from http import HTTPMethod, HTTPStatus
from typing import cast

import httpx
from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from pydantic import ValidationError as PydanticValidationError

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.core.utils.http_utils import get_rss_sync_client
from legadilo.core.utils.types import FormChoices
from legadilo.reading.models import Tag

from ...users.models import User
from ...users.user_types import AuthenticatedHttpRequest
from .. import constants
from ..models import Feed, FeedCategory
from ..services.feed_parsing import (
    FeedFileTooBigError,
    InvalidFeedFileError,
    MultipleFeedFoundError,
    NoFeedUrlFoundError,
    get_feed_data,
)

logger = logging.getLogger(__name__)


class SubscribeToFeedForm(forms.Form):
    url = forms.URLField(
        label=_("Feed URL"),
        required=True,
        max_length=2048,
        assume_scheme="https",
        help_text=_(
            "Enter the URL to the feed you want to subscribe to. If you don't know it, enter the "
            "URL of the site and the server will try to find the feed for you."
        ),
    )
    feed_choices = forms.ChoiceField(
        label=_("Feed choices"),
        choices=[],
        required=False,
        widget=forms.HiddenInput(),
    )
    # Filled automatically when adding a page from a site in which multiple feeds are found. This
    # allows for the user to select the correct feed.
    proposed_feed_choices = forms.CharField(
        label=_("Proposed feed choices"),
        required=False,
        widget=forms.HiddenInput(),
    )
    refresh_delay = forms.ChoiceField(
        label=_("Refresh delay"),
        required=True,
        choices=constants.FeedRefreshDelays.choices,
        initial=constants.FeedRefreshDelays.DAILY_AT_NOON,
    )
    article_retention_time = forms.IntegerField(
        label=_("Article retention period"),
        required=True,
        initial=365,
        min_value=0,
        help_text=_(
            "Define for how long in days to keep read articles associated with this feed. Use 0 to "
            "always keep the articles."
        ),
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
            "Tags to associate to articles of this feed. To create a new tag, type and press enter."
        ),
    )
    open_original_url_by_default = forms.BooleanField(
        label=_("Open original by default"), required=False
    )

    def __init__(
        self,
        data=None,
        *,
        tag_choices: FormChoices,
        category_choices: FormChoices,
        **kwargs,
    ):
        super().__init__(data, **kwargs)
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]
        self.fields["category"].choices = category_choices  # type: ignore[attr-defined]
        if data and (proposed_feed_choices := data.get("proposed_feed_choices")):
            self.fields["url"].widget.attrs["readonly"] = "true"
            self.initial["proposed_feed_choices"] = proposed_feed_choices
            self.fields["feed_choices"].widget = forms.RadioSelect()
            cast(
                forms.ChoiceField, self.fields["feed_choices"]
            ).choices = self._load_proposed_feed_choices(proposed_feed_choices)
            self.fields["feed_choices"].required = True

    def _load_proposed_feed_choices(self, raw_choices):
        try:
            choices = json.loads(raw_choices)
        except json.JSONDecodeError:
            return []

        if not isinstance(choices, list):
            return []
        for value in choices:
            if len(value) != 2 or not isinstance(value[0], str) or not isinstance(value[1], str):  # noqa: PLR2004
                return []

        return choices

    class Meta:
        fields = ("url", "refresh_delay", "article_retention_time", "category", "tags")

    @property
    def feed_url(self):
        return self.cleaned_data.get("feed_choices") or self.cleaned_data["url"]


@dataclass(frozen=True)
class SubscriptionResult:
    feed: Feed | None
    was_created: bool = False
    warning_message: str = ""
    error_message: str = ""


@require_http_methods(["GET", "POST"])
@login_required
def subscribe_to_feed_view(request: AuthenticatedHttpRequest):
    subscription_result = None
    if request.method == HTTPMethod.GET:
        status = HTTPStatus.OK
        form = _get_subscribe_to_feed_form(data=None, user=request.user)
    else:
        status, form, subscription_result = _handle_creation(request)

    return TemplateResponse(
        request,
        "feeds/subscribe_to_feed.html",
        {"form": form, "subscription_result": subscription_result},
        status=status,
    )


def _get_subscribe_to_feed_form(data: dict | None, user: User):
    tag_choices = Tag.objects.get_all_choices(user)
    category_choices = FeedCategory.objects.get_all_choices(user)
    return SubscribeToFeedForm(data, tag_choices=tag_choices, category_choices=category_choices)


def _handle_creation(
    request: AuthenticatedHttpRequest,
) -> tuple[HTTPStatus, SubscribeToFeedForm, SubscriptionResult | None]:
    form = _get_subscribe_to_feed_form(request.POST, user=request.user)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form, None

    try:
        with get_rss_sync_client() as client:
            feed_medata = get_feed_data(form.feed_url, client=client)
        category = FeedCategory.objects.get_first_for_user(
            request.user, form.cleaned_data.get("category")
        )
        with transaction.atomic():
            tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data["tags"])
            feed, created = Feed.objects.create_from_metadata(
                feed_medata,
                request.user,
                form.cleaned_data["refresh_delay"],
                form.cleaned_data["article_retention_time"],
                tags,
                category,
                open_original_url_by_default=form.cleaned_data["open_original_url_by_default"],
            )
    except (
        httpx.HTTPError,
        FeedFileTooBigError,
        InvalidFeedFileError,
        PydanticValidationError,
        ValueError,
        TypeError,
    ):
        error_message = _(
            "Failed to fetch the feed. Please check that the URL you entered is correct, that "
            "the feed exists, is accessible, valid "
            "and that the file is not above %(max_size)s MiB."
        ) % {"max_size": constants.MAX_FEED_FILE_SIZE / 1024 / 1024}
        return (
            HTTPStatus.NOT_ACCEPTABLE,
            form,
            SubscriptionResult(feed=None, error_message=error_message),
        )
    except NoFeedUrlFoundError:
        return (
            HTTPStatus.BAD_REQUEST,
            form,
            SubscriptionResult(
                feed=None, error_message=str(_("Failed to find a feed URL on the supplied page."))
            ),
        )
    except MultipleFeedFoundError as e:
        form = _get_subscribe_to_feed_form(
            {
                "url": form.feed_url,
                "proposed_feed_choices": json.dumps(e.feed_urls),
            },
            user=request.user,
        )
        return (
            HTTPStatus.BAD_REQUEST,
            form,
            SubscriptionResult(
                feed=None,
                warning_message=str(
                    _("Multiple feeds were found at this location, please select the proper one.")
                ),
            ),
        )

    # Empty form after success.
    form = _get_subscribe_to_feed_form(data=None, user=request.user)
    status = HTTPStatus.CREATED if created else HTTPStatus.OK
    return status, form, SubscriptionResult(feed=feed, was_created=created)
