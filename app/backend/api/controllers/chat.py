from typing import Any
from typing import Callable
from typing import ClassVar

from api.controllers.base import Controller
from api.controllers.base import ErrorProvider
from api.models import ChatRequest
from api.models import ChatResponse
from api.models import ErrorResponse
from azure.core.exceptions import ResourceNotFoundError
from chats import ChatRegistry
from openai import RateLimitError
from quart import jsonify
from quart import Request
from quart import request
from quart import ResponseReturnValue
from quart.views import MethodView
from quart_schema import document_request
from quart_schema import document_response
from services.auth import auth
from services.logger import LOG_SENSITIVE_DATA
from services.logger import new_logger


logger = new_logger(__name__)


class ChatController(Controller):
    """ChatController is a class that provides the chat controller."""

    def __init__(self, chat_registry: ChatRegistry):
        self.approaches = chat_registry

    @auth
    async def chat(self, req: Request) -> ResponseReturnValue:
        """chat is a method that returns a response to a chat request."""

        if not req.is_json:
            return self.error_response_with_message(ErrorProvider.INVALID_JSON)
        try:
            data: dict[str, Any] = await req.get_json()
            chat_req = ChatRequest(**data)
            if chat_req.validate():
                return self.error_response_with_message(ErrorProvider.MALFORMED_REQUEST)

            logger.debug(
                "Received request",
                {
                    "route": request.path,
                    "method": request.method,
                    "request": chat_req.to_dict(include_sensitive=LOG_SENSITIVE_DATA),
                },
            )

            approach = self.approaches.get(chat_req.approach)
            if not approach:
                return self.error_response_with_message(ErrorProvider.UNKNOWN_APPROACH)

            resp = await approach.run(chat_req.history, chat_req.overrides, self.auth.get_roles(req))
            return jsonify(resp), 200

        except Exception as e:
            if self.is_bad_request(e):
                logger.debug("Received malformed request", {"error": str(e)})
                return self.error_response_with_message(ErrorProvider.MALFORMED_REQUEST)
            if isinstance(e, RateLimitError):
                logger.warning("Chat request rate limit exceeded", {"error": str(e)})
                return self.error_response_with_message(ErrorProvider.RATE_LIMIT)
            if isinstance(e, ResourceNotFoundError):
                logger.warning("Resource not found", {"error": str(e)})
                return self.error_response(e.message, e.status_code if e.status_code else 503)

            logger.exception("Error while processing chat request", {"error": str(e)})
            return self.error_response(str(e), 500)


# The docstring is the description shown in the API documentation.
class ChatRoute(MethodView):
    """Endpoint for chatting with the custom model

    This endpoint is used to chat with a given chat approach.
    It is a protected endpoint and requires a valid JWT token to access it.
    """

    decorators: ClassVar[list[Callable]] = [
        document_request(ChatRequest),
        document_response(ChatResponse, 200),
        document_response(ErrorResponse, 400),
        document_response(ErrorResponse, 401),
        document_response(ErrorResponse, 403),
        document_response(ErrorResponse, 415),
        document_response(ErrorResponse, 429),
        document_response(ErrorResponse, 500),
        document_response(ErrorResponse, 503),
    ]

    def __init__(self, chat_controller: ChatController):
        self.chat_controller = chat_controller

    async def post(self) -> ResponseReturnValue:
        """post is a route that sends a chat request to the service."""
        return await self.chat_controller.chat(request)
