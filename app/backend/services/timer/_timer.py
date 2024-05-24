import inspect
import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any
from typing import Callable
from typing import cast
from typing import Generator
from typing import Optional
from typing import TypeVar

from services.logger import LOG_EXECUTION_TIMES
from services.logger import LOGGING_PRECISION
from services.logger import new_logger


logger = new_logger(__name__)


class Timer:
    """Timer is a simple timer that measures the elapsed time of a block of code."""

    def __init__(self):
        self.start = 0
        self.end = 0

    @contextmanager
    def timeit(self) -> Generator[None, None, None]:
        """timeit is a context manager that measures the elapsed time of the block of code it wraps."""
        self.start = time.perf_counter()
        yield
        self.end = time.perf_counter()

    def elapsed(self) -> float:
        """elapsed returns the elapsed time in seconds and resets the timer."""
        elapsed = round(self.end - self.start, LOGGING_PRECISION)
        self.reset()
        return elapsed

    def reset(self) -> None:
        """reset resets the timer."""
        self.start = 0
        self.end = 0


T = TypeVar("T", bound=Callable[..., Any])


def timer(log_level: int = logging.DEBUG) -> Callable[[T], T]:
    """timer is a decorator that times the execution of a function."""

    if not LOG_EXECUTION_TIMES:
        return lambda func: func

    def decorator(func: T) -> T:
        is_async = inspect.iscoroutinefunction(func)

        def log_execution_time(name: str, rtt: float, exception: Optional[Exception] = None):
            if exception:
                logger.warning(f"{name} executed in {rtt} seconds until exception: {str(exception)}")
                return
            if log_level != logging.DEBUG:
                logger.log(log_level, f"{name} executed in {rtt} seconds.")
                return

            logger.debug(f"{name} executed in {rtt} seconds.")

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            exec_timer = Timer()
            name: str = func.__name__
            if qualname := getattr(func, "__qualname__", None):
                name = qualname

            try:
                with exec_timer.timeit():
                    resp = await func(*args, **kwargs)
            except Exception as e:
                log_execution_time(name, exec_timer.elapsed(), e)
                raise

            log_execution_time(name, exec_timer.elapsed())
            return resp

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            exec_timer = Timer()
            name: str = func.__name__
            if qualname := getattr(func, "__qualname__", None):
                name = qualname

            try:
                with exec_timer.timeit():
                    resp = func(*args, **kwargs)
            except Exception as e:
                log_execution_time(name, exec_timer.elapsed(), e)
                raise

            log_execution_time(name, exec_timer.elapsed())
            return resp

        return cast(T, async_wrapper if is_async else sync_wrapper)

    return decorator
