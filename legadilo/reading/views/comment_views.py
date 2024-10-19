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
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST
from nh3 import clean_text

from legadilo.reading.models import Article, Comment
from legadilo.users.user_types import AuthenticatedHttpRequest


class CommentArticleForm(forms.Form):
    article_id = forms.IntegerField(required=True, widget=forms.HiddenInput)
    text = forms.CharField(required=True, widget=forms.Textarea(attrs={"rows": 5}))

    class Meta:
        fields = ("text",)

    def clean_text(self):
        text = self.cleaned_data.get("text", "")
        text = clean_text(text)
        if not text:
            raise ValidationError("Your text is empty!")

        return text


@require_POST
@login_required
def create_comment_view(
    request: AuthenticatedHttpRequest,
) -> TemplateResponse | HttpResponseBadRequest:
    form = CommentArticleForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest()

    article = get_object_or_404(Article, id=form.cleaned_data["article_id"], user=request.user)
    comment = Comment.objects.create(article=article, text=form.cleaned_data["text"])

    return TemplateResponse(request, "reading/partials/comment.html", {"comment": comment})
