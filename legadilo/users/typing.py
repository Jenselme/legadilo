from typing import Never

from django.http import HttpRequest
from django_htmx.middleware import HtmxDetails

from legadilo.users.models import User


class AuthenticatedHttpRequest(HttpRequest):
    user: User
    htmx: HtmxDetails


def assert_never(arg: Never) -> Never:
    raise AssertionError(f"{arg} triggered a code branch that should be unreachable")
