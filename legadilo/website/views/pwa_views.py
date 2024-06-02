from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.views.decorators.http import require_GET


@require_GET
def manifest_view(request: HttpRequest) -> TemplateResponse:
    return TemplateResponse(
        request,
        "website/manifest.json",
        content_type="application/json",
        headers={"Cache-Control": f"max-age={24 * 60 * 60}, public"},
    )


@require_GET
def default_favicon_view(request: HttpRequest) -> HttpResponseRedirect:
    return HttpResponseRedirect(static("images/icons/legadilo.16x16.png"))
