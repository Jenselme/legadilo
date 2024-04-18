from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta

from legadilo.users.managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for Legadilo.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), db_collation="case_insensitive", unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    # mypy false positive about overriding class variable.
    objects = UserManager()  # type: ignore[misc]

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")

    default_reading_time = models.PositiveIntegerField(
        default=200,
        help_text=_(
            "Number of words you read in minutes. Used to calculate the reading time of articles."
        ),
    )

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint("user", name="%(app_label)s_%(class)s_unique_per_user"),
        ]

    def __str__(self):
        return f"UserSettings(user={self.user})"
