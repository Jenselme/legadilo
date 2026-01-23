# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from allauth.account.admin import EmailAddressAdmin as DjangoAllAuthEmailAddress
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import decorators, get_user_model
from django.db.models.functions import Collate
from django.utils.translation import gettext_lazy as _

from legadilo.users.forms import UserAdminChangeForm, UserAdminCreationForm
from legadilo.users.models import ApplicationToken, Notification, UserSession, UserSettings

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


@admin.register(UserSession)
class SessionAdmin(admin.ModelAdmin):
    readonly_fields = (
        "session_key",
        "created_at",
        "updated_at",
        "expire_date",
        "user",
        "session_data",
    )
    list_display = ("session_key", "created_at", "updated_at", "expire_date", "user")

    def has_add_permission(self, request):
        return False
