from allauth.account.signals import user_signed_up

from legadilo.users.models import UserSettings


def create_user_settings_on_user_registration(sender, user, **kwargs):
    UserSettings.objects.create(user=user)


user_signed_up.connect(create_user_settings_on_user_registration)
