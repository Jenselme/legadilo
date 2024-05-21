from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from legadilo.feeds.models import Feed
from legadilo.users.typing import AuthenticatedHttpRequest


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
