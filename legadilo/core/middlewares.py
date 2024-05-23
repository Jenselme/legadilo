from csp.middleware import CSPMiddleware as DjangoCSPMiddleware
from django.conf import settings


class CSPMiddleware(DjangoCSPMiddleware):
    def build_policy(self, request, response):
        if request.path.startswith(f"/{settings.ADMIN_URL}"):
            response._csp_replace = {
                "script-src": "'self'",
                "style-src": "'self'",
            }
        return super().build_policy(request, response)
