from api.errors import ErrorProvider
from api.models.common_models import ErrorResponse
from api.routes.legacy.models import FeedbackRequest
from api.routes.legacy.models import FeedbackResponse
from chats.interfaces import ChatMessage
from containers import DIContainer
from dependency_injector.wiring import inject
from dependency_injector.wiring import Provide
from quart import Blueprint
from quart import jsonify
from quart import request
from quart import ResponseReturnValue
from quart_schema import document_request
from quart_schema import document_response
from quart_schema import tag
from services.auth import secure_endpoint
from services.feedback import FeedbackService
from services.feedback._interface import Feedback
from services.logger import new_logger

logger = new_logger(__name__)
bp = Blueprint("feedback", __name__)


@bp.route("/feedback", methods=["POST"])
@tag(["/v1"])
@document_request(FeedbackRequest)
@document_response(FeedbackResponse, 200)
@document_response(ErrorResponse, 400)
@document_response(ErrorResponse, 401)
@document_response(ErrorResponse, 403)
@document_response(ErrorResponse, 500)
@secure_endpoint
@inject
async def feedback(
    feedback_service: FeedbackService = Provide[DIContainer.feedback_logger_service],
) -> ResponseReturnValue:
    """Endpoint for sending feedback about the current chat.

    This endpoint is used to send feedback about a given chat session.
    It is a protected endpoint and requires a valid JWT token to access it.
    """

    if not request.is_json:
        return ErrorProvider.error_response_with_message(ErrorProvider.INVALID_JSON)
    try:
        data: dict = await request.get_json()
        feedback = FeedbackRequest(**data)
        if len(feedback.history) > 0:
            await feedback_service.send_feedback(
                Feedback(
                    history=[
                        ChatMessage(
                            bot=m.bot,
                            model=m.model,
                            user=m.user,
                        )
                        for m in feedback.history
                    ],
                    message=feedback.message,
                    rating=feedback.rating,
                )
            )
        return jsonify({"response": "Feedback received."}), 200
    except Exception as e:
        if ErrorProvider.is_bad_request(e):
            logger.debug("Received malformed request", {"error": str(e)})
            return ErrorProvider.error_response_with_message(ErrorProvider.MALFORMED_REQUEST)

        logger.exception("Error while sending feedback", {"error": str(e)})
        return ErrorProvider.error_response("error while sending feedback", 500, error=e)
