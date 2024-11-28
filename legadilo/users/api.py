# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime

import jwt
from django.http import HttpRequest
from django.shortcuts import aget_object_or_404
from ninja import ModelSchema, Router, Schema
from ninja.errors import AuthenticationError
from ninja.security import HttpBearer
from pydantic import BaseModel as BaseSchema
from pydantic import ValidationError as PydanticValidationError

from config import settings
from legadilo.users.models import ApplicationToken
from legadilo.utils.time_utils import utcnow

from .models import User
from .user_types import AuthenticatedApiRequest

users_api_router = Router(tags=["auth"])


class AuthBearer(HttpBearer):
    async def authenticate(self, request, token) -> User | None:
        if not token:
            return None

        decoded_jwt = _decode_jwt(token)
        return await _get_user_from_jwt(decoded_jwt)


class JWT(BaseSchema):
    application_token_title: str
    user_id: int
    exp: datetime


def _decode_jwt(token: str) -> JWT:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return JWT.model_validate(decoded_token)
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError("Expired JWT token") from e
    except (jwt.PyJWTError, PydanticValidationError) as e:
        raise AuthenticationError("Invalid JWT token") from e


async def _get_user_from_jwt(decoded_jwt: JWT) -> User | None:
    try:
        return await User.objects.aget(id=decoded_jwt.user_id)
    except User.DoesNotExist:
        return None


class RefreshTokenPayload(Schema):
    application_token: str


class Token(Schema):
    jwt: str


@users_api_router.post(
    "/refresh/",
    auth=None,
    response=Token,
    url_name="refresh_token",
    summary="Create a new access token from an application token",
)
async def refresh_token_view(request: HttpRequest, payload: RefreshTokenPayload) -> Token:
    application_token = await aget_object_or_404(
        ApplicationToken.objects.get_queryset().only_valid().defer(None),
        token=payload.application_token,
    )
    application_token.last_used_at = utcnow()
    await application_token.asave()
    jwt = _create_jwt(application_token.user_id, application_token.title)

    return Token(jwt=jwt)


def _create_jwt(user_id: int, application_token: str) -> str:
    return jwt.encode(
        {
            "application_token_title": application_token,
            "user_id": user_id,
            "exp": utcnow() + settings.JWT_MAX_AGE,
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ("email",)


@users_api_router.get(
    "", response=UserSchema, url_name="user_info", summary="Get current user info"
)
async def get_user_view(request: AuthenticatedApiRequest) -> User:  # noqa: RUF029 auth is async!
    """Access information about your user.

    It mostly serves as an endpoint to check that you are correctly authenticated and can use the
    API with a token.
    """
    return request.auth
