from legadilo.users.models import UserSettings


def create_user_settings_on_user_registration(sender, user, **kwargs):
    UserSettings.objects.create(user=user)
