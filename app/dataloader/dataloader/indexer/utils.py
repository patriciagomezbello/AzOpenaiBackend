from collections.abc import AsyncIterable
from collections.abc import AsyncIterator
from typing import TypeVar

T = TypeVar("T")


async def aenumerate(iterable: AsyncIterable[T], start: int = 0) -> AsyncIterator[tuple[int, T]]:
    """An async iterator that yields the index and the value of the iterable."""
    i = start
    async for e in iterable:
        yield i, e
        i += 1
