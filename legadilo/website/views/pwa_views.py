from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET


@require_GET
def manifest_view(request: HttpRequest) -> TemplateResponse:
    return TemplateResponse(
        request,
        "website/manifest.json",
        content_type="application/json",
        headers={"Cache-Control": f"max-age={2 * 60 * 60}, public"},
    )
