import base64
import binascii
import inspect
from collections.abc import AsyncGenerator
from collections.abc import Callable
from collections.abc import Coroutine
from contextlib import asynccontextmanager
from typing import Any


@asynccontextmanager
async def defer(
    func: Callable[[], Coroutine[Any, Any, None]],
    error_handler: Callable[[Exception], None] | Callable[[Exception], Coroutine[Any, Any, None]] = lambda _: None,
) -> AsyncGenerator[None, None]:
    try:
        yield
    except Exception as e:
        if inspect.iscoroutinefunction(error_handler):
            await error_handler(e)
            return
        error_handler(e)
    finally:
        await func()


def is_url_encoded(s: str) -> bool:
    """Check if the string is base64 URL encoded."""
    try:
        base64.urlsafe_b64decode(s.encode())
        return True
    except (binascii.Error, ValueError):
        return False
