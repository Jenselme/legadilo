from csp.decorators import csp_update
from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.feeds import constants
from legadilo.feeds.models import Article, ArticleTag, Tag
from legadilo.feeds.views.view_utils import get_from_url_for_article_details
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.urls import validate_referer_url


class EditTagsForm(forms.Form):
    tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to this article. To create a new tag, type and press enter."
        ),
    )

    class Meta:
        fields = ("tags",)

    def __init__(self, *args, tag_choices: list[tuple[str, str]], **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]


@require_GET
@login_required
@csp_update(IMG_SRC="https:")
def article_details_view(
    request: AuthenticatedHttpRequest, article_id: int, article_slug: str
) -> TemplateResponse:
    article = get_object_or_404(
        Article.objects.get_queryset().for_details(),
        id=article_id,
        slug=article_slug,
        user=request.user,
    )
    tag_choices = Tag.objects.get_all_choices(request.user)
    edit_tags_form = EditTagsForm(
        initial={
            "tags": article.article_tags.get_selected_values(),
        },
        tag_choices=tag_choices,
    )
    return TemplateResponse(
        request,
        "feeds/article_details.html",
        {
            "article": article,
            "edit_tags_form": edit_tags_form,
            "from_url": get_from_url_for_article_details(request, request.GET),
        },
    )


@require_POST
@login_required
def update_article_tags_view(
    request: AuthenticatedHttpRequest, article_id: int
) -> HttpResponseRedirect:
    article = get_object_or_404(Article, id=article_id, user=request.user)
    tag_choices = Tag.objects.get_all_choices(request.user)
    form = EditTagsForm(
        request.POST,
        initial={
            "tags": article.article_tags.get_selected_values(),
        },
        tag_choices=tag_choices,
    )
    if form.is_valid():
        tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data["tags"])
        ArticleTag.objects.associate_articles_with_tags(
            [article], tags, constants.TaggingReason.ADDED_MANUALLY, readd_deleted=True
        )
        ArticleTag.objects.dissociate_article_with_tags_not_in_list(article, tags)

    return HttpResponseRedirect(
        validate_referer_url(request, reverse("feeds:default_reading_list"))
    )
