from typing import Any

from asgiref.sync import async_to_sync
from django.core.management import BaseCommand


class AsyncCommand(BaseCommand):
    async def run(self, *args: Any, **options: Any) -> str | None:
        raise NotImplementedError

    def handle(self, *args: Any, **options: Any) -> str | None:
        return async_to_sync(self.run)(*args, **options)
