import inspect
import logging
import os
from collections.abc import Callable
from collections.abc import Iterator
from collections.abc import Mapping
from types import TracebackType
from typing import Any
from typing import cast
from urllib.parse import urlparse

from azure.identity.aio import ChainedTokenCredential


class CustomLogger(logging.Logger):
    factory = logging.getLogRecordFactory()

    def makeRecord(
        self,
        name: str,
        level: int,
        fn: str,
        lno: int,
        msg: object,
        args: tuple[object, ...] | Mapping[str, object],
        exc_info: tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None] | None,
        func: str | None = None,
        extra: Mapping[str, object] | None = None,
        sinfo: str | None = None,
    ) -> logging.LogRecord:
        rc = self.factory(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra is not None:
            if not self.isEnabledFor(logging.DEBUG):
                rc.msg = f"{rc.msg}\n"
                return rc

            rc.msg = f"{rc.msg} - {extra}\n"
            return rc

        rc.msg = f"{rc.msg}\n"
        return rc


def new_logger(name: str | None) -> logging.Logger:
    """Creates a new logger with the given name."""

    def has_handler(logger: logging.Logger, handler: type[logging.Handler]) -> bool:
        return any(isinstance(h, type(handler)) for h in logger.handlers)

    klass = logging.getLoggerClass()
    logging.setLoggerClass(CustomLogger)
    try:
        logger = logging.getLogger(name)
        if os.getenv("LOGGING", "True").lower() == "false":
            if not has_handler(logger, logging.NullHandler):
                logger.addHandler(logging.NullHandler())
            return logger

        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(level)

        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
        if level == "DEBUG":
            fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%H:%M:%S")
        if not has_handler(logger, logging.StreamHandler):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(fmt)
            logger.addHandler(console_handler)
        return logger
    finally:
        logging.setLoggerClass(klass)


logger = new_logger(__name__)


class ClientManager:
    """A base class for managing clients that need to be closed when the object is destroyed."""

    def __init__(self, credential: ChainedTokenCredential):
        self._closed = False
        self.credential = credential

    def _closable_clients(self) -> Iterator[str]:
        """Automatically find all attributes that have a close method."""
        for attribute in dir(self):
            attr: object | None = getattr(self, attribute, None)
            if attr and hasattr(attr, "close"):
                yield attribute

    async def close_clients(self) -> None:
        """Closes all clients of the object recursively. After calling this method, the object is likely no longer usable."""
        if self._closed:
            return

        async def close_client(client: Any) -> None:
            """Helper function to close a single client."""
            if not client:
                return

            close: Callable[[], None] | Any = getattr(client, "close", None)
            if not close or not (inspect.ismethod(close) or inspect.isfunction(close)):
                return

            logger.debug(f"Closing client: {client}")
            if inspect.iscoroutinefunction(close):
                await close()
            else:
                close()

            if hasattr(client, "_closable_clients"):
                client = cast(ClientManager, client)
                for sub_client in client._closable_clients():
                    sub_client = getattr(client, sub_client, None)
                    await close_client(sub_client)

        for c in self._closable_clients():
            client = getattr(self, c, None)
            await close_client(client)

        self._closed = True


def is_url(url: str) -> bool:
    """Check if the given string is a valid URL."""
    parsed = urlparse(url)
    return bool(parsed.scheme) and bool(parsed.netloc)
