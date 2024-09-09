from typing import Any

from api.errors import ErrorProvider
from api.models import ErrorResponse
from api.routes.legacy.models import ChatRequest
from api.routes.legacy.models import ChatResponse
from azure.core.exceptions import ResourceNotFoundError
from chats.interfaces import ChatMessage
from chats.registry import ChatRegistry
from containers import DIContainer
from dependency_injector.wiring import inject
from dependency_injector.wiring import Provide
from openai import RateLimitError
from quart import Blueprint
from quart import jsonify
from quart import request
from quart import ResponseReturnValue
from quart_schema import document_request
from quart_schema import document_response
from quart_schema import tag
from services.auth import secure_endpoint
from services.auth._interface import AuthService
from services.logger import new_logger
from services.logger._custom import LOG_SENSITIVE_DATA


logger = new_logger(__name__)
bp = Blueprint("chat", __name__)


@bp.route("/chat", methods=["POST"])
@tag(["/v1"])
@document_request(ChatRequest)
@document_response(ChatResponse, 200)
@document_response(ErrorResponse, 400)
@document_response(ErrorResponse, 401)
@document_response(ErrorResponse, 403)
@document_response(ErrorResponse, 415)
@document_response(ErrorResponse, 429)
@document_response(ErrorResponse, 500)
@document_response(ErrorResponse, 503)
@secure_endpoint
@inject
async def chat(
    chat_registry: ChatRegistry = Provide[DIContainer.chat_registry],
    auth_service: AuthService = Provide[DIContainer.oauth_service],
) -> ResponseReturnValue:
    """Endpoint for chatting with the custom model

    This endpoint is used to chat with a given chat approach.
    It is a protected endpoint and requires a valid JWT token to access it.
    """

    if not request.is_json:
        return ErrorProvider.error_response_with_message(ErrorProvider.INVALID_JSON)
    try:
        data: dict[str, Any] = await request.get_json()
        chat_req = ChatRequest(**data)
        if chat_req.validate():
            return ErrorProvider.error_response_with_message(ErrorProvider.MALFORMED_REQUEST)

        logger.debug(
            "Received request",
            {
                "route": request.path,
                "method": request.method,
                "request": chat_req.to_dict(include_sensitive=LOG_SENSITIVE_DATA),
            },
        )

        approach = chat_registry.get(chat_req.approach)
        if not approach:
            return ErrorProvider.error_response_with_message(ErrorProvider.UNKNOWN_APPROACH)

        resp = await approach.run(
            [ChatMessage(bot=m.bot, model=m.model, user=m.user) for m in chat_req.history],
            chat_req.overrides,
            auth_service.get_roles(request),
        )
        return jsonify(resp), 200

    except Exception as e:
        if ErrorProvider.is_bad_request(e):
            logger.debug("Received malformed request", {"error": str(e)})
            return ErrorProvider.error_response_with_message(ErrorProvider.MALFORMED_REQUEST)
        if isinstance(e, RateLimitError):
            logger.warning("Chat request rate limit exceeded", {"error": str(e)})
            return ErrorProvider.error_response_with_message(ErrorProvider.RATE_LIMIT)
        if isinstance(e, ResourceNotFoundError):
            logger.warning("Resource not found", {"error": str(e)})
            return ErrorProvider.error_response(e.message, e.status_code if e.status_code else 503)

        logger.exception("Error while processing chat request", {"error": str(e)})
        return ErrorProvider.error_response("error while processing chat request", 500, error=e)
