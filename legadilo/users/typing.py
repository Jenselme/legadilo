from django.http import HttpRequest

from legadilo.users.models import User


class AuthenticatedHttpRequest(HttpRequest):
    user: User
