# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
from allauth.account.models import EmailAddress
from django.core.management import BaseCommand

from legadilo.core.models import Timezone
from legadilo.core.utils.http_utils import get_rss_sync_client
from legadilo.feeds.constants import FeedRefreshDelays
from legadilo.feeds.models import Feed
from legadilo.feeds.services.feed_parsing import get_feed_data
from legadilo.reading.models import Article, ReadingList
from legadilo.reading.services.article_fetching import fetch_article_data
from legadilo.users.models import User, UserSettings


class Command(BaseCommand):
    help = "Setup a test database with an admin user, a feed and an article."

    email = "admin@example.com"
    password = "password"  # noqa: S105 hardcoded password
    feeds = [
        "https://www.jujens.eu/feeds/all.atom.xml",
    ]
    articles = ["https://getbootstrap.com/docs/5.3/getting-started/introduction/"]

    def handle(self, *args, **options):
        user = self._create_user()
        self._subscribe_to_feeds(user)
        self._add_articles(user)

    def _create_user(self):
        if not User.objects.filter(email=self.email).exists():
            user = User.objects.create_superuser(
                email=self.email,
                password=self.password,
            )
            UserSettings.objects.create(user=user, timezone=Timezone.objects.get_default())
            EmailAddress.objects.create(user=user, email=self.email, verified=True)
            ReadingList.objects.create_default_lists(user=user)
            self.stdout.write(self.style.SUCCESS(f"User {user} created"))
        else:
            self.stdout.write("User already exists")

        return User.objects.select_related("settings").get(email=self.email)

    def _subscribe_to_feeds(self, user):
        for feed_url in self.feeds:
            if Feed.objects.filter(feed_url=feed_url).exists():
                continue

            with get_rss_sync_client() as client:
                feed_medata = get_feed_data(feed_url, client=client)

            Feed.objects.create_from_metadata(
                feed_medata,
                user,
                FeedRefreshDelays.HOURLY,
                article_retention_time=0,
                tags=[],
                category=None,
                open_original_url_by_default=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Feed {feed_url} and article created"))

    def _add_articles(self, user):
        for article_url in self.articles:
            article_data = fetch_article_data(article_url)
            Article.objects.save_from_fetch_results(
                user,
                [article_data],
                tags=[],
            )
            self.stdout.write(self.style.SUCCESS(f"Article {article_url} added"))
