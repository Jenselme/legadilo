from typing import Never

from django.http import HttpRequest

from legadilo.users.models import User


class AuthenticatedHttpRequest(HttpRequest):
    user: User


def assert_never(arg: Never) -> Never:
    raise AssertionError(f"{arg} triggered a code branch that should be unreachable")
