import logging.handlers
import os
import threading
import traceback
from enum import Enum

# LOGGING_PRECISION defines the decimal precision for the logging times.
LOGGING_PRECISION: int = 4


class Color(Enum):
    """Color is an enumeration of ANSI color codes for use in terminal output."""

    LIGHT_GREY = "\x1b[240m"
    BLUE = "\x1b[34m"
    CYAN = "\x1b[36m"
    YELLOW = "\x1b[33m"
    ORANGE = "\x1b[31m"
    RED = "\x1b[31m"
    PURPLE = "\x1b[35m"
    DARK_RED = "\x1b[31m"
    BLACK = "\x1b[30m"
    GREEN = "\x1b[32m"
    MAGENTA = "\x1b[35m"
    WHITE = "\x1b[37m"
    RESET = "\x1b[0m"


def _find_log_caller_frame() -> traceback.FrameSummary:
    """_find_log_caller_frame finds the frame of the caller of the logger."""
    frames = traceback.extract_stack()
    for frame in reversed(frames):
        if frame.filename != __file__ and logging.__file__ not in frame.filename:
            return frame
    return frames[-1]  # Should never happen


_LOG_CALLER = os.getenv("LOG_CALLER", "false").lower() == "true"
_LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
LOG_EXECUTION_TIMES = os.getenv("LOG_EXECUTION_TIMES", "false").lower() == "true"
LOG_SENSITIVE_DATA = os.getenv("LOG_SENSITIVE_DATA", "false").lower() == "true"

_logger_registry = set()


def get_registered_loggers() -> set[logging.Logger]:
    """get_registered_loggers returns the set of all registered loggers."""
    return _logger_registry


class CustomFormatter(logging.Formatter):
    """CustomFormatter is a custom formatter for log messages.
    It adds the color to the log messages based on the log level.
    """

    LEVEL_COLORS: list[tuple[int, str]] = [
        (logging.DEBUG, Color.BLUE.value),
        (logging.INFO, Color.CYAN.value),
        (logging.WARNING, Color.YELLOW.value),
        (logging.ERROR, Color.RED.value),
        (logging.CRITICAL, Color.PURPLE.value),
    ]

    FORMATS: dict[int, logging.Formatter] = {}
    for level, color in LEVEL_COLORS:
        match _LOG_FORMAT:
            case "color":
                fmt = (
                    f"\x1b[30;1m%(asctime)s\x1b[0m {color}%(levelname)-8s\x1b[0m "
                    + ("\x1b[35m<%(pathname)s:%(lineno)d> \x1b[0m" if _LOG_CALLER else "")
                    + "\x1b[35m%(name)s\x1b[0m %(message)s"
                )
            case "text":
                fmt = (
                    "%(asctime)s %(levelname)-8s " + ("<%(pathname)s:%(lineno)d> " if _LOG_CALLER else "") + "%(name)s %(message)s"
                )
            case _:  # Default to JSON format
                fmt = (
                    '{"time": "%(asctime)s", '
                    + ('"stacktrace": "<%(pathname)s:%(lineno)d>", ' if _LOG_CALLER else "")
                    + '"level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
                )

        FORMATS[level] = logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # If there is no exception, get the frame information
        if not record.exc_info:
            frame = _find_log_caller_frame()
            record.pathname = frame.filename
            record.lineno = frame.lineno if frame.lineno else 0
            record.funcName = frame.name
        else:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f"\x1b[31m{text}\x1b[0m"

        output = formatter.format(record)
        # Remove the cache layer
        record.exc_text = None
        return output


# Define a lock for logger switching
logger_lock = threading.Lock()


def new_logger(module_name: str, use_console_handler: bool = True, use_file_handler: bool = False) -> logging.Logger:
    """
    new_logger configures a new logger with the specified configurations.

    Args:
        module_name (str): The name of the module for which the logger is being set up.
            This is typically __name__ in the module where the logger is created.

        use_console_handler (bool, optional): If True, enables logging to the console (i.e., stdout). Defaults to True.

        use_file_handler (bool, optional): If True, enables logging to a file. Defaults to False.

    Returns:
        logging.Logger: The configured logger. This logger can be used to log messages at different levels
            (e.g., info, debug, warning, error, critical), and these messages will be handled according to the
            logger's configuration (i.e., logged to the console, file, both, or neither).
    """

    with logger_lock:
        if os.getenv("LOGGING", "True").lower() == "false":
            logger = logging.getLogger("null")
            logger.addHandler(logging.NullHandler())
            return logger

        library, _, _ = module_name.partition(".py")
        logger = logging.getLogger(library)
        level = logging.getLevelName(os.getenv("LOG_LEVEL", "INFO").upper())
        logger.setLevel(level)

        if use_console_handler:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(CustomFormatter())
            logger.addHandler(console_handler)

        if use_file_handler:
            grandparent_dir = os.path.abspath(f"{__file__}/../../")
            log_name = os.getenv("LOG_FILE_NAME", "logger.log")
            log_path = os.path.join(grandparent_dir, log_name)
            try:
                log_handler = logging.handlers.RotatingFileHandler(
                    filename=log_path,
                    encoding="utf-8",
                    maxBytes=int(os.getenv("LOG_MAX_BYTES", 32 * 1024 * 1024)),  # 32 MiB
                    backupCount=int(os.getenv("LOG_BACKUP_COUNT", 2)),  # Rotate through 2 files
                )
                file_formatter = logging.Formatter(
                    "%(asctime)-s %(levelname)-8s %(name)s %(message)s",
                    "%Y-%m-%d %H:%M:%S",
                )
                log_handler.setFormatter(file_formatter)
                log_handler.setLevel(level)
                logger.addHandler(log_handler)
            except Exception as e:
                logger.error(f"Failed to create file handler: {e}")

        _logger_registry.add(logger)
        return logger
