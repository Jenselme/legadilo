# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
from http import HTTPStatus

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from legadilo.reading.models import Article, Comment
from legadilo.reading.templatetags import markdown
from legadilo.users.user_types import AuthenticatedHttpRequest


class CommentArticleForm(forms.ModelForm):
    article_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    text = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": _("Type your comment here. Markdown syntax is supported."),
            }
        ),
    )

    class Meta:
        fields = ("text",)
        model = Comment

    def clean_text(self):
        text = self.cleaned_data.get("text", "")
        rendered_markdown = markdown(text)
        if not rendered_markdown:
            raise ValidationError(
                "Your comment renders to an empty string. Please use correct markdown synthax."
            )

        return text


@require_POST
@login_required
def create_comment_view(
    request: AuthenticatedHttpRequest,
) -> TemplateResponse | HttpResponseBadRequest:
    form = CommentArticleForm(request.POST)
    if not form.is_valid():
        return TemplateResponse(
            request,
            "reading/partials/comment.html#add-comment-form",
            {
                "comment_article_form": form,
                "article_id": form.data.get("article_id"),
            },
            headers={"HX-Retarget": "#add-comment-form", "HX-Reswap": "innerHTML"},
            status=HTTPStatus.BAD_REQUEST,
        )

    article = get_object_or_404(Article, id=form.cleaned_data["article_id"], user=request.user)
    comment = Comment.objects.create(article=article, text=form.cleaned_data["text"])

    return TemplateResponse(
        request,
        "reading/partials/comment.html#add-comment-success",
        {
            "comment": comment,
            "comment_article_form": CommentArticleForm(),
            "article_id": article.id,
        },
        headers={"HX-Retarget": "#all-comments", "HX-Reswap": "beforeend"},
    )


@require_GET
@login_required
def display_comment_view(request: AuthenticatedHttpRequest, pk: int) -> TemplateResponse:
    comment = get_object_or_404(Comment, pk=pk, article__user=request.user)

    return TemplateResponse(
        request, "reading/partials/comment.html#comment-card", {"comment": comment}
    )


@require_http_methods(["GET", "POST"])
@login_required
def edit_comment_view(request: AuthenticatedHttpRequest, pk: int) -> TemplateResponse:
    comment = get_object_or_404(Comment, pk=pk, article__user=request.user)
    form = CommentArticleForm(
        initial={"article_id": comment.article_id, "text": comment.text}, instance=comment
    )

    if request.method == "POST":
        form = CommentArticleForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return TemplateResponse(
                request, "reading/partials/comment.html#comment-card", {"comment": comment}
            )

    return TemplateResponse(
        request,
        "reading/partials/comment.html#edit-comment-form",
        {
            "comment": comment,
            "comment_article_form": form,
        },
    )


@require_POST
@login_required
def delete_comment_view(request: AuthenticatedHttpRequest, pk: int) -> HttpResponse:
    comment = get_object_or_404(Comment, pk=pk, article__user=request.user)

    comment.delete()

    return HttpResponse()
