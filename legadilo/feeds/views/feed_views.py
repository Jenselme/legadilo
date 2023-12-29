import json
from http import HTTPMethod, HTTPStatus

import httpx
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.utils.decorators import alogin_required

from ..forms import CreateFeedForm
from ..models import Feed
from ..utils.feed_metadata import MultipleFeedFoundError, NoFeedUrlFoundError


@require_http_methods(["GET", "POST"])
@alogin_required
async def create_feed(request: HttpRequest):
    if request.method == HTTPMethod.GET:
        status = HTTPStatus.OK
        form = CreateFeedForm()
    else:
        status, form = await _handle_creation(request)

    return TemplateResponse(request, "feeds/create_feed.html", {"form": form}, status=status)


async def _handle_creation(request):
    form = CreateFeedForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("Failed to create the feed"))
        return HTTPStatus.BAD_REQUEST, form

    try:
        feed = await Feed.objects.create_from_url(form.feed_url, request.user)
    except httpx.HTTPError:
        messages.error(
            request,
            _(
                "Failed to fetch the feed. Please check that the URL you entered is correct, that the feed exists "
                "and is accessible."
            ),
        )
        return HTTPStatus.NOT_ACCEPTABLE, form
    except IntegrityError:
        messages.error(request, _("You are already subscribed to this feed."))
        return HTTPStatus.CONFLICT, form
    except NoFeedUrlFoundError:
        messages.error(request, _("Failed to find a feed URL on the supplied page."))
        return HTTPStatus.BAD_REQUEST, form
    except MultipleFeedFoundError as e:
        form = CreateFeedForm({
            "url": form.feed_url,
            "proposed_feed_choices": json.dumps(e.feed_urls),
        })
        messages.warning(request, _("Multiple feeds were found at this location, please select the proper one."))
        return HTTPStatus.BAD_REQUEST, form
    else:
        # Empty form after success.
        form = CreateFeedForm()
        messages.success(request, _("Feed '%s' added") % feed.title)
        return HTTPStatus.CREATED, form
