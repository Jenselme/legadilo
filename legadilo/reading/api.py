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

from ninja import ModelSchema, Router
from ninja.pagination import paginate

from legadilo.reading.models import Article
from legadilo.users.user_types import AuthenticatedHttpRequest

reading_api_router = Router(tags=["reading"])


class OutArticleSchema(ModelSchema):
    class Meta:
        model = Article
        exclude = ("user", "obj_created_at", "obj_updated_at")


@reading_api_router.get("/articles/", response=list[OutArticleSchema])
@paginate
def list_articles(request: AuthenticatedHttpRequest):
    return Article.objects.get_queryset().for_user(request.user).default_order_by()
