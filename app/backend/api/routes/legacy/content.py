from api.errors import ErrorProvider
from api.models import ErrorResponse
from api.routes.legacy.models import ContentQueryString
from api.routes.legacy.models import ContentResponse
from containers import DIContainer
from dependency_injector.wiring import inject
from dependency_injector.wiring import Provide
from quart import Blueprint
from quart import request
from quart import ResponseReturnValue
from quart import send_file
from quart_schema import document_querystring
from quart_schema import document_response
from quart_schema import tag
from services.auth import secure_endpoint
from services.auth._interface import AuthService
from services.content import ContentService
from services.logger import new_logger
from services.schemas import FileWrapper
from services.search import SearchService


logger = new_logger(__name__)
bp = Blueprint("content", __name__)


@bp.route("/content/<string:path>", methods=["GET"])
@tag(["/v1"])
@document_response(ErrorResponse, 401)
@document_response(ErrorResponse, 403)
@document_response(ErrorResponse, 404)
@document_response(ErrorResponse, 500)
@secure_endpoint
@inject
async def content(
    path: str,
    content_service: ContentService = Provide[DIContainer.azure_blob_content_service],
    search_service: SearchService = Provide[DIContainer.azure_search_service],
    auth_service: AuthService = Provide[DIContainer.oauth_service],
) -> ResponseReturnValue:
    """Endpoint for downloading files from the storage blob.

    This endpoint is used to download the given file from the storage blob.
    It is a protected endpoint and requires a valid JWT token to access it.
    """

    try:

        if not await search_service.has_file_access(path, auth_service.get_roles(request)):
            return ErrorProvider.error_response_with_message(ErrorProvider.AUTHORIZATION)

        file: FileWrapper = await content_service.get_file(path)
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
            return ErrorProvider.error_response_with_message(ErrorProvider.DOC_NOT_FOUND)
        logger.exception("Error while getting file", {"path": path, "error": str(e)})
        return ErrorProvider.error_response("error while getting file", 500, error=e)


@bp.route("/content", methods=["GET"])
@tag(["/v1"])
@document_querystring(ContentQueryString)
@document_response(ContentResponse, 200)
@document_response(ErrorResponse, 400)
@document_response(ErrorResponse, 401)
@document_response(ErrorResponse, 403)
@document_response(ErrorResponse, 500)
@secure_endpoint
@inject
async def get_content(
    search_service: SearchService = Provide[DIContainer.azure_search_service],
    auth_service: AuthService = Provide[DIContainer.oauth_service],
) -> ResponseReturnValue:
    """Endpoint getting indexed content from the index.

    This endpoint is to check what documents are available
    It is a protected endpoint and requires a valid JWT token to access it.

    The `max_count` query parameter defines how many documents and their count should be returned.
    """
    try:
        max_count = int(request.args.get("max_count", 100))
        res = await search_service.get_indexed_content(auth_service.get_roles(request), max_count=max_count)
        return {"content": res}
    except Exception as e:
        logger.exception("Error while getting indexed content", {"error": str(e)})
        return ErrorProvider.error_response("error while getting indexed content", 500, error=e)
