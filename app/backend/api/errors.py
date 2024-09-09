from typing import Any

from api.models import ErrorMessage
from quart import jsonify
from quart import ResponseReturnValue
from services.logger import LOG_SENSITIVE_DATA as RESPOND_WITH_SENSITIVE_DATA
from werkzeug.exceptions import BadRequest


class ErrorProvider:
    """ErrorProvider is a class that holds the error messages and codes."""

    MALFORMED_REQUEST = ErrorMessage(400, "malformed request")
    UNKNOWN_APPROACH = ErrorMessage(400, "unknown approach")
    AUTHENTICATION = ErrorMessage(
        401,
        "invalid, expired, or missing token provided; you must provide a valid token",
    )
    AUTHORIZATION = ErrorMessage(403, "you are not authorized to access this resource")
    DOC_NOT_FOUND = ErrorMessage(404, "document not found or not available")
    INVALID_JSON = ErrorMessage(415, "request must be json")
    RATE_LIMIT = ErrorMessage(429, "rate limit exceeded")

    @staticmethod
    def error_response_with_message(message: ErrorMessage) -> ResponseReturnValue:
        """error_response_with_message returns a response with the given ErrorMessage.
        You may only use the class's constants as arguments."""
        return ErrorProvider.error_response(message.message, message.code)

    @staticmethod
    def error_response(message: str, code: int, **kwargs: Any) -> ResponseReturnValue:
        """error_response returns a response with the given message and code.
        You may also provide an error object to be included in the response if SENSITIVE_DATA is enabled.
        """
        response = {"error": {"code": code, "message": message}}
        if RESPOND_WITH_SENSITIVE_DATA:
            if err := kwargs.get("error"):
                response["error"]["error"] = str(err)

        return (jsonify(response), code)

    @staticmethod
    def is_bad_request(e: Exception) -> bool:
        """is_bad_request checks if the exception is a bad request."""
        return isinstance(e, BadRequest) or isinstance(e, TypeError)
