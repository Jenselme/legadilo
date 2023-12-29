from collections.abc import AsyncIterable
from typing import TypeVar

T = TypeVar("T")


async def alist(async_generator: AsyncIterable[T]) -> list[T]:
    return [value async for value in async_generator]
