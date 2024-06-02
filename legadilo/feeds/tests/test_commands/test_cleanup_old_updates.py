import pytest
from django.core.management import call_command


@pytest.mark.django_db()
class TestCleanupOldUpdatesCommand:
    def test_cleanup_no_objects(self):
        call_command("cleanup_old_updates")
