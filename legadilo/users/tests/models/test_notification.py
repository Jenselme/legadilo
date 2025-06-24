# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
import time_machine

from legadilo.users.models import Notification
from legadilo.utils.time_utils import utcdt, utcnow

from ..factories import NotificationFactory


@pytest.mark.django_db
class TestNotificationQuerySet:
    def test_for_user(self, user, other_user):
        notification = NotificationFactory(user=user)
        NotificationFactory(user=other_user)

        notifications = list(Notification.objects.get_queryset().for_user(user))

        assert notifications == [notification]

    def test_for_ids(self, user):
        notification = NotificationFactory(user=user)
        NotificationFactory(user=user)

        notifications = list(Notification.objects.get_queryset().for_ids([notification.id]))

        assert notifications == [notification]

    def test_only_unread(self, user):
        notification = NotificationFactory(user=user, read_at=None)
        NotificationFactory(user=user, read_at=utcnow())

        notifications = list(Notification.objects.get_queryset().only_unread())

        assert notifications == [notification]

    @time_machine.travel("2024-10-12")
    def test_for_user_list(self, user):
        with time_machine.travel("2024-06-01"):
            very_old_unread_notification = NotificationFactory(
                title="Very old unread", user=user, read_at=None
            )
        with time_machine.travel("2024-06-01"):
            NotificationFactory(title="Very old read", user=user, read_at=utcnow())
        with time_machine.travel("2024-06-01"):
            very_old_but_read_recently_notification = NotificationFactory(
                title="Very old but read recently", user=user, read_at=utcdt(2024, 10, 1)
            )
        today_unread = NotificationFactory(title="Today unread", user=user, read_at=None)
        today_read = NotificationFactory(title="Today read", user=user, read_at=utcnow())

        notifications = list(Notification.objects.get_queryset().for_user_list(user))

        assert notifications == [
            very_old_unread_notification,
            today_unread,
            today_read,
            very_old_but_read_recently_notification,
        ]


@pytest.mark.django_db
class TestNotificationManager:
    @pytest.mark.parametrize(("read_at", "expected_status"), [(None, 1), (utcnow(), 0)])
    def test_count_unread(self, user, read_at, expected_status):
        NotificationFactory(user=user, read_at=read_at)

        assert Notification.objects.count_unread(user) == expected_status

    def test_list_recent(self, user, other_user):
        notification = NotificationFactory(user=user)
        NotificationFactory(user=other_user)

        notifications = list(Notification.objects.list_recent_for_user(user))

        assert notifications == [notification]

    def test_mark_as_read(self, user):
        notification = NotificationFactory(user=user, read_at=None)
        other_notification = NotificationFactory(user=user, read_at=None)

        Notification.objects.mark_as_read(user, notification.id)

        notification.refresh_from_db()
        assert notification.read_at is not None
        assert notification.is_read
        other_notification.refresh_from_db()
        assert other_notification.read_at is None
        assert not other_notification.is_read

    def test_mark_all_as_read(self, user, other_user):
        notification = NotificationFactory(user=user, read_at=None)
        other_notification = NotificationFactory(user=user, read_at=None)
        notification_other_user = NotificationFactory(user=other_user, read_at=None)

        Notification.objects.mark_as_read(user)

        notification.refresh_from_db()
        assert notification.read_at is not None
        assert notification.is_read
        other_notification.refresh_from_db()
        assert other_notification.read_at is not None
        assert other_notification.is_read
        notification_other_user.refresh_from_db()
        assert notification_other_user.read_at is None
        assert not notification_other_user.is_read

    def test_mark_as_unread(self, user):
        notification = NotificationFactory(user=user, read_at=utcnow())
        other_notification = NotificationFactory(user=user, read_at=utcnow())

        Notification.objects.mark_as_unread(user, notification.id)

        notification.refresh_from_db()
        assert notification.read_at is None
        assert not notification.is_read
        other_notification.refresh_from_db()
        assert other_notification.read_at is not None
        assert other_notification.is_read

    def test_mark_all_as_unread(self, user, other_user):
        notification = NotificationFactory(user=user, read_at=utcnow())
        other_notification = NotificationFactory(user=user, read_at=utcnow())
        notification_other_user = NotificationFactory(user=other_user, read_at=utcnow())

        Notification.objects.mark_as_unread(user)

        notification.refresh_from_db()
        assert notification.read_at is None
        assert not notification.is_read
        other_notification.refresh_from_db()
        assert other_notification.read_at is None
        assert not other_notification.is_read
        notification_other_user.refresh_from_db()
        assert notification_other_user.read_at is not None
        assert notification_other_user.is_read
