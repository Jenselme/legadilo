from django.http import HttpRequest
from django_htmx.middleware import HtmxDetails

from legadilo.users.models import User


class AuthenticatedHttpRequest(HttpRequest):
    user: User
    htmx: HtmxDetails
