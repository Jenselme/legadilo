from django.core.management import BaseCommand

from legadilo.feeds.models import Feed
from legadilo.reading.models import ArticleFetchError


class Command(BaseCommand):
    def handle(self, *args, **options):
        Feed.objects.get_feed_update_for_cleanup().delete()
        ArticleFetchError.objects.get_queryset().for_cleanup().delete()
