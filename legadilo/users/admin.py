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
from allauth.account.admin import EmailAddressAdmin as DjangoAllAuthEmailAddress
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import decorators, get_user_model
from django.db.models.functions import Collate
from django.utils.translation import gettext_lazy as _

from legadilo.users.forms import UserAdminChangeForm, UserAdminCreationForm
from legadilo.users.models import ApplicationToken, Notification, UserSettings

User = get_user_model()

admin.site.unregister(EmailAddress)

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://django-allauth.readthedocs.io/en/stable/advanced.html#admin
    admin.site.login = decorators.login_required(admin.site.login)  # type: ignore[method-assign]


class UserSettingsInline(admin.TabularInline):
    model = UserSettings
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["email", "date_joined", "last_login", "is_active", "is_superuser"]
    search_fields = ["name", "email_deterministic"]
    ordering = ["last_login"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    inlines = [UserSettingsInline]

    def get_queryset(self, request):
        return (
            super().get_queryset(request).alias(email_deterministic=Collate("email", "und-x-icu"))
        )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)
    list_display = ("title", "created_at", "user", "is_read")
    list_filter = ("is_read",)


@admin.register(ApplicationToken)
class ApplicationTokenAdmin(admin.ModelAdmin):
    autocomplete_fields = ("user",)


@admin.register(EmailAddress)
class EmailAddressAdmin(DjangoAllAuthEmailAddress):
    def get_search_fields(self, request):
        return ["email_deterministic", "user__name", "user_email_deterministic"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .alias(
                email_deterministic=Collate("email", "und-x-icu"),
                user_email_deterministic=Collate("user__email", "und-x-icu"),
            )
        )
