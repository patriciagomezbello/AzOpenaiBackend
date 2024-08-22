from typing import Any
from api.models import ErrorMessage
from config import Config
from quart import jsonify
from quart import ResponseReturnValue
from services.auth import AuthService
from services.logger import LOG_SENSITIVE_DATA as RESPOND_WITH_SENSITIVE_DATA
from werkzeug.exceptions import BadRequest


class ErrorProvider:
    """ErrorProvider is a class that holds the error messages and codes."""

    MALFORMED_REQUEST = ErrorMessage(400, "malformed request")
    UNKNOWN_APPROACH = ErrorMessage(400, "unknown approach")
    AUTHENTICATION = ErrorMessage(401, "invalid, expired, or missing token provided; you must provide a valid token")
    AUTHORIZATION = ErrorMessage(403, "you are not authorized to access this resource; allowed roles: {allowed_roles}")
    DOC_NOT_FOUND = ErrorMessage(404, "document not found or not available")
    INVALID_JSON = ErrorMessage(415, "request must be json")
    RATE_LIMIT = ErrorMessage(429, "rate limit exceeded")

    def error_response_with_message(self, message: ErrorMessage) -> ResponseReturnValue:
        """error_response_with_message returns a response with the given ErrorMessage.
        You may only use the class's constants as arguments."""
        return self.error_response(message.message, message.code)

    def error_response(self, message: str, code: int, **kwargs: Any) -> ResponseReturnValue:
        """error_response returns a response with the given message and code.
        You may also provide an error object to be included in the response if SENSITIVE_DATA is enabled.
        """
        response = {"error": {"code": code, "message": message}}
        if RESPOND_WITH_SENSITIVE_DATA:
            if err := kwargs.get("error"):
                response["error"]["error"] = str(err)

        return (jsonify(response), code)


class Controller(ErrorProvider):

    config: Config
    auth: AuthService
    _initialized: bool = False

    def __init__(self):
        if not self._initialized:
            raise AttributeError("The base controller has not been initialized.")
        super().__init__()
        super().AUTHORIZATION.message = super().AUTHORIZATION.message.format(allowed_roles=self.config.auth.allowed_roles)

    # We don't use the normal __init__ method for this,
    # for avoiding accidentally overriding the class variables.
    @classmethod
    def initialize(cls, cfg: Config, auth: AuthService) -> None:
        """initialize initializes the controller with the given properties."""

        cls.config = cfg
        cls.auth = auth
        cls._initialized = True

    def is_bad_request(self, e: Exception) -> bool:
        """is_bad_request checks if the exception is a bad request."""
        return isinstance(e, BadRequest) or isinstance(e, TypeError)
