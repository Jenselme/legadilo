from functools import wraps

from django.core.exceptions import PermissionDenied


def alogin_required(function):
    """Placeholder until https://code.djangoproject.com/ticket/35030 is done."""

    @wraps(function)
    async def wrapper(request, *args, **kwargs):
        if (await request.auser()).is_authenticated:
            return await function(request, *args, **kwargs)

        raise PermissionDenied

    return wrapper
