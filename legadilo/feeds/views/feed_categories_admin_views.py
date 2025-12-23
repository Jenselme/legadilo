# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.feeds.models import FeedCategory
from legadilo.users.user_types import AuthenticatedHttpRequest


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
    title = forms.CharField(label=_("Title"), required=True)

    class Meta:
        model = FeedCategory
        fields = ("title",)


@require_http_methods(["GET", "POST"])
@login_required
@transaction.atomic()
def create_feed_category_view(
    request: AuthenticatedHttpRequest,
) -> TemplateResponse | HttpResponseRedirect:
    form = FeedCategoryForm()
    status = HTTPStatus.OK
    if request.method == "POST":
        status, form, feed_category = _create_feed_category(request)
        if feed_category:
            return HttpResponseRedirect(
                reverse("feeds:edit_feed_category", kwargs={"category_id": feed_category.id})
            )

    return TemplateResponse(request, "feeds/edit_feed_category.html", {"form": form}, status=status)


def _create_feed_category(
    request: AuthenticatedHttpRequest,
) -> tuple[HTTPStatus, FeedCategoryForm, FeedCategory | None]:
    form = FeedCategoryForm(data=request.POST)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form, None

    try:
        feed_category = FeedCategory.objects.create(**form.cleaned_data, user=request.user)
    except IntegrityError:
        messages.error(
            request, _("A category with title '%s' already exists.") % form.cleaned_data["title"]
        )
        return HTTPStatus.CONFLICT, form, None

    return HTTPStatus.CREATED, form, feed_category


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
