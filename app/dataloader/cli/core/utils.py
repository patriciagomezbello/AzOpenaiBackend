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
