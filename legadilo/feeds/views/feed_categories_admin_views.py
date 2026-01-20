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
from legadilo.users.models import User
from legadilo.users.user_types import AuthenticatedHttpRequest


@require_GET
@login_required
def feed_category_admin_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    return TemplateResponse(
        request,
        "feeds/feed_categories_admin.html",
        {
            "categories": FeedCategory.objects.get_queryset().for_user(request.user),
            "breadcrumbs": [
                (reverse("feeds:feed_category_admin"), _("Feed categories admin")),
            ],
        },
    )


class FeedCategoryForm(forms.ModelForm):
    title = forms.CharField(label=_("Title"), required=True)

    class Meta:
        model = FeedCategory
        fields = ("title",)

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

    @transaction.atomic()
    def save(self, commit=True):  # noqa: FBT002 Boolean-typed positional argument in function definition
        self.instance.user = self._user
        return super().save(commit=commit)


@require_http_methods(["GET", "POST"])
@login_required
def edit_feed_category_view(
    request: AuthenticatedHttpRequest, category_id: int | None = None
) -> TemplateResponse | HttpResponseRedirect:
    category = None
    if category_id is not None:
        category = get_object_or_404(FeedCategory, id=category_id, user=request.user)

    if category and request.method == "POST" and "delete" in request.POST:
        category.delete()
        return HttpResponseRedirect(reverse("feeds:feed_category_admin"))

    form = FeedCategoryForm(instance=category, user=request.user)
    status = HTTPStatus.OK
    if request.method == "POST":
        status, form, category = _handle_category_edition(request, category)
        if status == HTTPStatus.OK and "save" in request.POST:
            return HttpResponseRedirect(reverse("feeds:feed_category_admin"))
        if status == HTTPStatus.OK and "save-add-new" in request.POST:
            return HttpResponseRedirect(reverse("feeds:create_feed_category"))
        if category and status == HTTPStatus.OK:
            return HttpResponseRedirect(
                reverse("feeds:edit_feed_category", kwargs={"category_id": category.id})
            )

    last_crumb = (
        (
            reverse("feeds:edit_feed_category", kwargs={"category_id": category.id}),
            _("Edit feed category"),
        )
        if category
        else (reverse("feeds:create_feed_category"), _("Create feed category"))
    )
    return TemplateResponse(
        request,
        "feeds/edit_feed_category.html",
        {
            "form": form,
            "category": category,
            "breadcrumbs": [
                (reverse("feeds:feed_category_admin"), _("Feed categories admin")),
                last_crumb,
            ],
        },
        status=status,
    )


def _handle_category_edition(
    request: AuthenticatedHttpRequest, category: FeedCategory | None
) -> tuple[HTTPStatus, FeedCategoryForm, FeedCategory | None]:
    form = FeedCategoryForm(request.POST, instance=category, user=request.user)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form, category

    try:
        category = form.save()
    except IntegrityError:
        messages.error(
            request, _("A category with title '%s' already exists.") % form.cleaned_data["title"]
        )
        return HTTPStatus.CONFLICT, form, category
    return HTTPStatus.OK, form, category
