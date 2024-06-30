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

from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.feeds.models import FeedCategory
from legadilo.users.typing import AuthenticatedHttpRequest


@require_GET
@login_required
def feed_category_admin_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    return TemplateResponse(
        request,
        "feeds/feed_categories_admin.html",
        {
            "categories": FeedCategory.objects.get_queryset().for_user(request.user),
        },
    )


class FeedCategoryForm(forms.ModelForm):
    title = forms.CharField()

    class Meta:
        model = FeedCategory
        fields = ("title",)


@require_http_methods(["GET", "POST"])
@login_required
def create_feed_category_view(
    request: AuthenticatedHttpRequest,
) -> TemplateResponse | HttpResponseRedirect:
    form = FeedCategoryForm()
    if request.method == "POST":
        form = FeedCategoryForm(data=request.POST)
        if form.is_valid():
            feed_category = FeedCategory.objects.create(**form.cleaned_data, user=request.user)
            return HttpResponseRedirect(
                reverse("feeds:edit_feed_category", kwargs={"category_id": feed_category.id})
            )

    return TemplateResponse(request, "feeds/edit_feed_category.html", {"form": form})


@require_http_methods(["GET", "POST"])
@login_required
def edit_feed_category_view(
    request: AuthenticatedHttpRequest, category_id: int
) -> TemplateResponse | HttpResponseRedirect:
    category = get_object_or_404(FeedCategory, id=category_id, user=request.user)
    if request.method == "POST" and "delete" in request.POST:
        category.delete()
        return HttpResponseRedirect(reverse("feeds:feed_category_admin"))

    form = FeedCategoryForm(instance=category)
    if request.method == "POST":
        form = FeedCategoryForm(instance=category, data=request.POST)
        if form.is_valid():
            form.save()

    return TemplateResponse(
        request, "feeds/edit_feed_category.html", {"form": form, "category": category}
    )
