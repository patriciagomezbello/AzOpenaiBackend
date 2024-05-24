from typing import Callable
from typing import ClassVar

from api.controllers.base import Controller
from api.controllers.base import ErrorProvider
from api.models import ErrorResponse
from api.models import FeedbackRequest
from api.models import FeedbackResponse
from quart import jsonify
from quart import Request
from quart import request
from quart import ResponseReturnValue
from quart.views import MethodView
from quart_schema import document_request
from quart_schema import document_response
from services.auth import auth
from services.feedback import FeedbackService
from services.logger import new_logger
from werkzeug.exceptions import BadRequest

logger = new_logger(__name__)


class FeedbackController(Controller):
    """FeedbackController is a class that provides the feedback controller."""

    def __init__(self, feedback_svc: FeedbackService):
        super().__init__()
        self.feedback_svc = feedback_svc

    @auth
    async def feedback(self, req: Request) -> ResponseReturnValue:
        """feedback sends the feedback request to the service."""
        if not req.is_json:
            return self.error_response_with_message(ErrorProvider.INVALID_JSON)
        try:
            data: dict = await req.get_json()
            feedback = FeedbackRequest(**data)
            if len(feedback.history) > 0:
                await self.feedback_svc.send_feedback(feedback)
            return jsonify({"response": "Feedback received."}), 200
        except Exception as e:
            if isinstance(e, BadRequest) or isinstance(e, TypeError):
                logger.debug(f"Malformed request: {e}", exc_info=True)
                return self.error_response_with_message(ErrorProvider.MALFORMED_REQUEST)
            logger.exception(f"An error occurred while sending feedback: {e}")
            return self.error_response(str(e), 500)


# The docstring is the description shown in the API documentation.
class FeedbackRoute(MethodView):
    """Endpoint for sending feedback about the current chat.

    This endpoint is used to send feedback about a given chat session.
    It is a protected endpoint and requires a valid JWT token to access it.
    """

    decorators: ClassVar[list[Callable]] = [
        document_request(FeedbackRequest),
        document_response(FeedbackResponse, 200),
        document_response(ErrorResponse, 400),
        document_response(ErrorResponse, 403),
        document_response(ErrorResponse, 500),
    ]

    def __init__(self, feedback_controller: FeedbackController):
        self.feedback_controller = feedback_controller

    async def post(self) -> ResponseReturnValue:
        """post is a route that sends feedback to the service."""
        return await self.feedback_controller.feedback(request)
