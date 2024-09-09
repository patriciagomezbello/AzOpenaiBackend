from functools import wraps
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import cast
from typing import TypeVar

from quart import request
from quart import ResponseReturnValue
from services.auth._oauth import NoAuthHeaderError
from services.auth._oauth import OAuthService
from services.logger import new_logger

T = TypeVar("T", bound=Callable[..., Awaitable[ResponseReturnValue]])
logger = new_logger(__name__)


def secure_endpoint(func: T) -> T:
    """Decorator to check if the user is authenticated and authorized.

    This decorator is used to check if the user is authenticated and authorized.
    It is used to protect the endpoints from unauthorized access.
    """
    from dependency_injector.wiring import Provide, inject
    from api.errors import ErrorProvider
    from containers import DIContainer

    @wraps(func)
    @inject
    async def wrapper(
        *args: Any,
        oauth_service: OAuthService = Provide[DIContainer.oauth_service],
        **kwargs: Any,
    ) -> ResponseReturnValue:
        try:
            if not oauth_service.is_authenticated(request):
                return ErrorProvider.error_response_with_message(ErrorProvider.AUTHENTICATION)

            if not oauth_service.is_authorized(request):
                return ErrorProvider.error_response_with_message(ErrorProvider.AUTHORIZATION)

            return await func(*args, **kwargs)

        except Exception as e:
            if isinstance(e, NoAuthHeaderError):
                return ErrorProvider.error_response_with_message(ErrorProvider.AUTHENTICATION)

            logger.exception("Error while authenticating or authorizing", {"error": str(e)})
            return ErrorProvider.error_response(str(e.args[0]), 500)

    return cast(T, wrapper)
