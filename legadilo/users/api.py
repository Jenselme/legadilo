# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
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
from http import HTTPStatus
from uuid import UUID

import jwt
from django.db import models
from django.http import HttpRequest
from ninja import ModelSchema, Router, Schema
from ninja.errors import AuthenticationError
from ninja.security import HttpBearer
from pydantic import BaseModel as BaseSchema
from pydantic import ValidationError as PydanticValidationError
from pydantic import field_serializer

from config import settings
from legadilo.users.models import ApplicationToken
from legadilo.utils.time_utils import utcnow

from ..utils.api import ApiError
from .models import User
from .user_types import AuthenticatedApiRequest

users_api_router = Router(tags=["auth"])


class AuthBearer(HttpBearer):
    def authenticate(self, request, token) -> User | None:
        if not token:
            return None

        decoded_token = _decode_access_token(token)
        return _get_user_from_access_token(decoded_token)


class AccessToken(BaseSchema):
    application_token_uuid: UUID
    exp: datetime

    @field_serializer("exp")
    def serialize_exp(self, value: datetime) -> int:
        return int(value.timestamp())


def _decode_access_token(token: str) -> AccessToken:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return AccessToken.model_validate(decoded_token)
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError(message="Expired JWT token") from e
    except (jwt.PyJWTError, PydanticValidationError) as e:
        raise AuthenticationError(message="Invalid JWT token") from e


def _get_user_from_access_token(access_token: AccessToken) -> User | None:
    try:
        filters = models.Q(application_tokens__validity_end__isnull=True) | models.Q(
            application_tokens__validity_end__gt=utcnow()
        )
        return User.objects.get(
            filters,
            is_active=True,
            application_tokens__uuid=access_token.application_token_uuid,
        )
    except (User.DoesNotExist, User.MultipleObjectsReturned):
        return None


class CreateTokensPayload(Schema):
    email: str
    application_token_uuid: UUID
    application_token_secret: str


class CreateTokensResponse(Schema):
    access_token: str


@users_api_router.post(
    "/tokens/",
    auth=None,
    response={HTTPStatus.OK: CreateTokensResponse, HTTPStatus.UNAUTHORIZED: ApiError},
    url_name="create_tokens",
    summary="Create an access token from an application token.",
)
def create_tokens_view(request: HttpRequest, payload: CreateTokensPayload):
    application_token = ApplicationToken.objects.use_application_token(
        payload.email, payload.application_token_uuid, payload.application_token_secret
    )
    if application_token is None:
        return HTTPStatus.UNAUTHORIZED, {"detail": "Invalid credentials."}

    access_token = _create_access_token(application_token)

    return CreateTokensResponse(access_token=access_token)


def _create_access_token(application_token: ApplicationToken) -> str:
    access_token = AccessToken(
        application_token_uuid=application_token.uuid, exp=utcnow() + settings.ACCESS_TOKEN_MAX_AGE
    )
    return jwt.encode(
        access_token.model_dump(mode="json"),
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
def get_user_view(request: AuthenticatedApiRequest) -> User:
    """Access information about your user.

    It mostly serves as an endpoint to check that you are correctly authenticated and can use the
    API with a token.
    """
    return request.auth
