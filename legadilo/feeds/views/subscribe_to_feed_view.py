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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
from http import HTTPMethod, HTTPStatus
from typing import cast

import httpx
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from pydantic import ValidationError as PydanticValidationError

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.reading.models import Tag
from legadilo.types import FormChoices

from ...users.models import User
from ...users.user_types import AuthenticatedHttpRequest
from ...utils.http_utils import get_rss_sync_client
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
        max_length=2048,
        assume_scheme="https",
        help_text=_(
            "Enter the URL to the feed you want to subscribe to or of a site in which case we will "
            "try to find the URL of the feed."
        ),
    )
    feed_choices = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.HiddenInput(),
    )
    proposed_feed_choices = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    refresh_delay = forms.ChoiceField(
        required=True,
        choices=constants.FeedRefreshDelays.choices,  # type: ignore[misc]
        initial=constants.FeedRefreshDelays.DAILY_AT_NOON,
    )
    article_retention_time = forms.IntegerField(
        required=True,
        initial=365,
        min_value=0,
        help_text=_(
            "Define for how long in days to keep read articles associated with this feed. Use 0 to "
            "always keep the articles."
        ),
    )
    category = forms.ChoiceField(
        required=False,
        help_text=_("The category of the feed to help you keep them organized."),
    )
    tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to articles of this feed. To create a new tag, type and press enter."
        ),
    )
    open_original_url_by_default = forms.BooleanField(required=False)

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


@require_http_methods(["GET", "POST"])
@login_required
def subscribe_to_feed_view(request: AuthenticatedHttpRequest):
    if request.method == HTTPMethod.GET:
        status = HTTPStatus.OK
        form = _get_subscribe_to_feed_form(data=None, user=request.user)
    else:
        status, form = _handle_creation(request)

    return TemplateResponse(request, "feeds/subscribe_to_feed.html", {"form": form}, status=status)


def _get_subscribe_to_feed_form(data: dict | None, user: User):
    tag_choices = Tag.objects.get_all_choices(user)
    category_choices = FeedCategory.objects.get_all_choices(user)
    return SubscribeToFeedForm(data, tag_choices=tag_choices, category_choices=category_choices)


def _handle_creation(request: AuthenticatedHttpRequest):  # noqa: PLR0911 Too many return statements
    form = _get_subscribe_to_feed_form(request.POST, user=request.user)
    if not form.is_valid():
        messages.error(request, _("Failed to create the feed"))
        return HTTPStatus.BAD_REQUEST, form

    try:
        with get_rss_sync_client() as client:
            feed_medata = get_feed_data(form.feed_url, client=client)
        tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data["tags"])
        category = FeedCategory.objects.get_first_for_user(
            request.user, form.cleaned_data.get("category")
        )
        feed, created = Feed.objects.create_from_metadata(
            feed_medata,
            request.user,
            form.cleaned_data["refresh_delay"],
            form.cleaned_data["article_retention_time"],
            tags,
            category,
            open_original_url_by_default=form.cleaned_data["open_original_url_by_default"],
        )
    except httpx.HTTPError:
        messages.error(
            request,
            _(
                "Failed to fetch the feed. Please check that the URL you entered is correct, that "
                "the feed exists and is accessible."
            ),
        )
        return HTTPStatus.NOT_ACCEPTABLE, form
    except NoFeedUrlFoundError:
        messages.error(request, _("Failed to find a feed URL on the supplied page."))
        return HTTPStatus.BAD_REQUEST, form
    except MultipleFeedFoundError as e:
        form = _get_subscribe_to_feed_form(
            {
                "url": form.feed_url,
                "proposed_feed_choices": json.dumps(e.feed_urls),
            },
            user=request.user,
        )
        messages.warning(
            request, _("Multiple feeds were found at this location, please select the proper one.")
        )
        return HTTPStatus.BAD_REQUEST, form
    except FeedFileTooBigError:
        messages.error(
            request,
            _("The feed file is too big, we won't parse it. Try to find a more lightweight feed."),
        )
        return HTTPStatus.BAD_REQUEST, form
    except (InvalidFeedFileError, PydanticValidationError, ValueError, TypeError) as e:
        logger.debug("Failed to parse feed: %s", e)
        messages.error(
            request,
            _(
                "We failed to parse the feed you supplied. Please check it is supported and "
                "matches the sync of a feed file."
            ),
        )
        return HTTPStatus.BAD_REQUEST, form

    if not created:
        messages.error(request, _("You are already subscribed to this feed."))
        return HTTPStatus.CONFLICT, form

    # Empty form after success.
    form = _get_subscribe_to_feed_form(data=None, user=request.user)
    messages.success(
        request,
        format_html(
            str(_("Feed '<a href=\"{}\">{}</a>' added")),
            str(reverse("feeds:feed_articles", kwargs={"feed_id": feed.id})),
            feed.title,
        ),
    )
    return HTTPStatus.CREATED, form
