import asyncio
from typing import Any

from django.core.management import BaseCommand


class AsyncCommand(BaseCommand):
    async def run(self, *args: Any, **options: Any) -> str | None:
        raise NotImplementedError

    def handle(self, *args: Any, **options: Any) -> str | None:
        return asyncio.run(self.run(*args, **options))
