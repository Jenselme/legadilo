from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, RedirectView, UpdateView

from legadilo.users.forms import UserSettingsForm
from legadilo.users.models import UserSettings

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        # for mypy to know that the user is authenticated
        assert self.request.user.is_authenticated  # noqa: S101 assert used
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("feeds:default_reading_list")


user_redirect_view = UserRedirectView.as_view()


@require_http_methods(["GET", "POST"])
@login_required
def user_update_settings_view(request):
    user_settings = UserSettings.objects.get(user=request.user)
    form = UserSettingsForm(instance=user_settings)
    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=user_settings)
        if form.is_valid():
            form.save()
            messages.success(request, _("Settings correctly updated"))
        else:
            messages.error(request, _("Failed to update settings"))

    return TemplateResponse(
        request,
        "users/user_settings.html",
        {
            "form": form,
            "user": request.user,
        },
    )
