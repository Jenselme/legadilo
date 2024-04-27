from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.feeds import constants
from legadilo.feeds.models import Article, ArticleTag, ReadingList, Tag
from legadilo.feeds.views.feed_views_utils import get_js_cfg_from_reading_list
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.urls import add_query_params, validate_from_url, validate_referer_url


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
            "tags": article.tags.get_selected_values(request.user),
        },
        tag_choices=tag_choices,
    )
    return TemplateResponse(
        request,
        "feeds/article_details.html",
        {
            "article": article,
            "edit_tags_form": edit_tags_form,
            "from_url": _get_from_url_for_article_details(request, request.GET),
        },
    )


def _get_from_url_for_article_details(request, query_dict) -> str:
    return validate_from_url(
        request, query_dict.get("from_url"), reverse("feeds:default_reading_list")
    )


@require_POST
@login_required
def delete_article_view(request: AuthenticatedHttpRequest, article_id: int) -> HttpResponse:
    article = get_object_or_404(Article, id=article_id, user=request.user)
    article.delete()

    for_article_details = request.POST.get("for_article_details", "").lower() == "true"
    if for_article_details:
        return _redirect_to_reading_list(request)

    if not request.htmx:
        from_url = _get_from_url_for_article_details(request, request.POST)
        return HttpResponseRedirect(from_url)

    return _update_article_card(
        request,
        article,
        hx_reswap="outerHTML show:none swap:1s",
        hx_target=f"#article-card-{article_id}",
    )


def _redirect_to_reading_list(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    from_url = _get_from_url_for_article_details(request, request.POST)
    return HttpResponseRedirect(
        add_query_params(from_url, {"full_reload": ["true"]}),
    )


@require_POST
@login_required
def update_article_view(
    request: AuthenticatedHttpRequest,
    article_id: int,
    update_action: constants.UpdateArticleActions,
) -> HttpResponse:
    article = get_object_or_404(
        Article.objects.get_queryset().for_details(), id=article_id, user=request.user
    )
    article.update_article_from_action(update_action)
    article.save()

    is_read_status_update = constants.UpdateArticleActions.is_read_status_update(update_action)
    for_article_details = request.POST.get("for_article_details", "").lower() == "true"

    if for_article_details:
        if is_read_status_update:
            return _redirect_to_reading_list(request)
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("feeds:default_reading_list"))
        )

    if not request.htmx:
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("feeds:default_reading_list"))
        )

    return _update_article_card(
        request, article, hx_reswap="outerHTML show:none", hx_target=f"#article-card-{article.id}"
    )


def _update_article_card(
    request: AuthenticatedHttpRequest, article: Article, *, hx_reswap, hx_target
) -> TemplateResponse:
    from_url = _get_from_url_for_article_details(request, request.POST)
    try:
        displayed_reading_list_id = int(request.POST.get("displayed_reading_list_id"))  # type: ignore[arg-type]
        reading_list = ReadingList.objects.get(id=displayed_reading_list_id)
        js_cfg = get_js_cfg_from_reading_list(reading_list)
    except (ValueError, TypeError, ReadingList.DoesNotExist):
        displayed_reading_list_id = None
        js_cfg = {}

    reading_lists = ReadingList.objects.get_all_for_user(request.user)
    count_articles_of_reading_lists = Article.objects.count_articles_of_reading_lists(reading_lists)
    return TemplateResponse(
        request,
        "feeds/update_article_action.html",
        {
            "article": article,
            "reading_lists": reading_lists,
            "count_articles_of_reading_lists": count_articles_of_reading_lists,
            "displayed_reading_list_id": displayed_reading_list_id,
            "js_cfg": js_cfg,
            "from_url": from_url,
        },
        headers={
            "HX-Reswap": hx_reswap,
            "HX-Retarget": hx_target,
        },
    )


@require_POST
@login_required
def update_article_tags_view(request: AuthenticatedHttpRequest, article_id: int) -> HttpResponse:
    article = get_object_or_404(Article, id=article_id, user=request.user)
    tag_choices = Tag.objects.get_all_choices(request.user)
    form = EditTagsForm(
        request.POST,
        initial={
            "tags": article.tags.get_selected_values(request.user),
        },
        tag_choices=tag_choices,
    )
    if form.is_valid():
        tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data["tags"])
        ArticleTag.objects.associate_articles_with_tags(
            [article], tags, constants.TaggingReason.ADDED_MANUALLY
        )
        ArticleTag.objects.dissociate_article_with_tags_not_in_list(article, tags)

    return HttpResponseRedirect(
        validate_referer_url(request, reverse("feeds:default_reading_list"))
    )
