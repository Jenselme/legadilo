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
from django.core.exceptions import BadRequest
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.security import HttpBearer
from pydantic import BaseModel as BaseSchema
from pydantic import ValidationError as PydanticValidationError

from config import settings
from legadilo.users.models import ApplicationToken
from legadilo.utils.time_utils import utcnow

from .models import User

users_api_router = Router(tags=["auth"])


class AuthBearer(HttpBearer):
    def authenticate(self, request, token) -> User | None:
        if not token:
            return None

        decoded_jwt = _decode_jwt(token)
        return _get_user_from_jwt(decoded_jwt)


class JWT(BaseSchema):
    application_token: str
    user_id: int
    exp: datetime


def _decode_jwt(token: str) -> JWT:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return JWT.model_validate(decoded_token)
    except jwt.ExpiredSignatureError as e:
        raise BadRequest("Expired JWT token") from e
    except (jwt.PyJWTError, PydanticValidationError) as e:
        raise BadRequest("Invalid JWT token") from e


def _get_user_from_jwt(decoded_jwt: JWT) -> User | None:
    try:
        return User.objects.get(id=decoded_jwt.user_id)
    except User.DoesNotExist:
        return None


class RefreshTokenPayload(Schema):
    application_token: str


class Token(Schema):
    jwt: str


@users_api_router.post("/refresh/", auth=None, response=Token)
def refresh_token(request: HttpRequest, payload: RefreshTokenPayload) -> Token:
    application_token = get_object_or_404(
        ApplicationToken.objects.get_queryset().only_valid().defer(None),
        token=payload.application_token,
    )
    application_token.last_used_at = utcnow()
    application_token.save()
    jwt = _create_jwt(application_token.user_id, application_token.token)

    return Token(jwt=jwt)


def _create_jwt(user_id: int, application_token: str) -> str:
    return jwt.encode(
        {
            "application_token": application_token,
            "user_id": user_id,
            "exp": utcnow() + settings.JWT_MAX_AGE,
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
