from legadilo.feeds.models import ReadingList


def create_default_reading_list_on_user_registration(sender, user, **kwargs):
    ReadingList.objects.create_default_lists(user=user)
