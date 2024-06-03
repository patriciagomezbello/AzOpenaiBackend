from typing import Callable
from typing import ClassVar

from api.controllers.base import Controller
from api.controllers.base import ErrorProvider
from api.models import ErrorResponse
from quart import Request
from quart import request
from quart import ResponseReturnValue
from quart import send_file
from quart.views import MethodView
from quart_schema import document_response
from services.auth import auth
from services.content import ContentService
from services.logger import new_logger
from services.schemas import File


logger = new_logger(__name__)


class ContentController(Controller):
    """ContentController is a class that provides the content controller."""

    def __init__(self, con_svc: ContentService):
        super().__init__()
        self.content_service = con_svc

    @auth
    async def get(self, _: Request, path: str) -> ResponseReturnValue:
        """get returns the file from the content service."""
        try:
            file: File = await self.content_service.get_file(path)
            return (
                await send_file(
                    file.data,
                    mimetype=file.mimetype,
                    as_attachment=False,
                    attachment_filename=path,
                ),
                200,
            )
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                logger.debug("File not found", {"path": path, "error": str(e)})
                return self.error_response_with_message(ErrorProvider.DOC_NOT_FOUND)
            logger.exception("Error while getting file", {"path": path, "error": str(e)})
            return self.error_response(str(e), 500)


# The docstring is the description shown in the API documentation.
class ContentRoute(MethodView):
    """Endpoint for downloading files from the storage blob.

    This endpoint is used to download the given file from the storage blob.
    It is a protected endpoint and requires a valid JWT token to access it.
    """

    decorators: ClassVar[list[Callable]] = [
        document_response(ErrorResponse, 401),
        document_response(ErrorResponse, 403),
        document_response(ErrorResponse, 404),
        document_response(ErrorResponse, 500),
    ]

    def __init__(self, content_controller: ContentController):
        self.content_controller = content_controller

    async def get(self, path: str) -> ResponseReturnValue:
        """get is a route that returns the file from the given path."""
        return await self.content_controller.get(request, path)
