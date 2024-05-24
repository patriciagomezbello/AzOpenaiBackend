from typing import Callable
from typing import ClassVar

from api.controllers.base import Controller
from api.models import CategoryResponse
from api.models import ErrorResponse
from quart import jsonify
from quart import Request
from quart import request
from quart import ResponseReturnValue
from quart.views import MethodView
from quart_schema import document_response
from services.auth import auth
from services.category import CategoryService
from services.logger import new_logger


logger = new_logger(__name__)


class CategoryController(Controller):
    """CategoryController is a class that provides the category controller."""

    def __init__(self, cat_svc: CategoryService):
        super().__init__()
        self.cat_svc = cat_svc

    @auth
    async def get(self, req: Request) -> ResponseReturnValue:
        """get returns the list of categories."""

        try:
            categories = await self.cat_svc.get_categories(self.auth.get_roles(req))
            return (jsonify({"categories": categories}), 200)
        except Exception as e:
            logger.exception(f"Error getting categories: {e}")
            return self.error_response(str(e), 500)


# The docstring is the description shown in the API documentation.
class CategoryRoute(MethodView):
    """Endpoint for receiving all available categories from the search index.

    This endpoint is used to retrieve all available categories from the search index.
    It is a protected endpoint and requires a valid JWT token to access it.
    """

    decorators: ClassVar[list[Callable]] = [
        document_response(CategoryResponse, 200),
        document_response(ErrorResponse, 403),
        document_response(ErrorResponse, 500),
    ]

    def __init__(self, category_controller: CategoryController):
        self.category_controller = category_controller

    async def get(self) -> ResponseReturnValue:
        """get is a route that returns a list of categories."""
        return await self.category_controller.get(request)
