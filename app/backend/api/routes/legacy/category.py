from api.errors import ErrorProvider
from api.models import ErrorResponse
from api.routes.legacy.models import CategoryResponse
from containers import DIContainer
from dependency_injector.wiring import inject
from dependency_injector.wiring import Provide
from quart import Blueprint
from quart import jsonify
from quart import request
from quart import ResponseReturnValue
from quart_schema import document_response
from quart_schema import tag
from services.auth import AuthService
from services.auth import secure_endpoint
from services.category import CategoryService
from services.logger import new_logger


logger = new_logger(__name__)
bp = Blueprint("category", __name__)


@bp.route("/categories", methods=["GET"])
@tag(["/v1"])
@document_response(CategoryResponse, 200)
@document_response(ErrorResponse, 401)
@document_response(ErrorResponse, 403)
@document_response(ErrorResponse, 500)
@secure_endpoint
@inject
async def categories(
    category_service: CategoryService = Provide[DIContainer.facet_category_service],
    auth_service: AuthService = Provide[DIContainer.oauth_service],
) -> ResponseReturnValue:
    """Endpoint for receiving all available categories from the search index.

    This endpoint is used to retrieve all available categories from the search index.
    It is a protected endpoint and requires a valid JWT token to access it.
    """

    try:
        categories = await category_service.get_categories(auth_service.get_roles(request))
        return (jsonify({"categories": categories}), 200)
    except Exception as e:
        logger.exception("Error while getting categories", {"error": str(e)})
        return ErrorProvider.error_response("Error while getting categories", 500, error=e)
