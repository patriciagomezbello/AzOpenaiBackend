from functools import wraps
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import cast
from typing import Optional
from typing import TypeVar

from quart import Request
from quart import ResponseReturnValue
from services.auth._interface import AuthService
from services.auth._oauth import NoAuthHeaderError
from services.logger import new_logger


T = TypeVar("T", bound=Callable[..., Awaitable[ResponseReturnValue]])
logger = new_logger(__name__)


def auth(func: T) -> T:
    """auth is a decorator that checks if the request is authenticated and authorized."""
    from api.controllers.base import Controller
    from api.controllers.base import ErrorProvider

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> ResponseReturnValue:
        self: Controller = args[0]
        request: Request = args[1]

        auth: Optional[AuthService] = getattr(self, "auth", None)
        if auth is None:
            raise AttributeError(
                f"{self.__class__.__name__} does not have the 'auth' attribute, which is required for the auth decorator"
            )

        try:
            if not auth.is_authenticated(request):
                return self.error_response_with_message(ErrorProvider.AUTHENTICATION)

            if not auth.is_authorized(request):
                return self.error_response_with_message(ErrorProvider.AUTHORIZATION)

            return await func(*args, **kwargs)

        except Exception as e:
            if isinstance(e, NoAuthHeaderError):
                return self.error_response_with_message(ErrorProvider.AUTHENTICATION)
            logger.exception(f"Error checking authentication: {e}")
            return self.error_response(str(e.args[0]), 500)

    return cast(T, wrapper)
