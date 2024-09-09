from api.models.health_models import HealthDetailedStatus
from api.models.health_models import HealthStatusResponse
from clients._search import SearchClient
from config.appconfig import Config
from containers import DIContainer
from dependency_injector.wiring import inject
from dependency_injector.wiring import Provide
from quart import Blueprint
from quart import jsonify
from quart import request
from quart import ResponseReturnValue
from quart_schema import document_response
from services.logger import new_logger

logger = new_logger(__name__)

health_bp = Blueprint("health", __name__)

API_KEY_HEADER = "X-Api-Key"


@health_bp.route("/health")
@document_response(HealthStatusResponse, 500)
@document_response(HealthStatusResponse, 200)
@inject
async def health(
    config: Config = Provide[DIContainer.settings],
    search_client: SearchClient = Provide[DIContainer.search_client],
) -> ResponseReturnValue:
    """Returns Ok (200) Status Code if the system is healthy, otherwise an InternalServerError (500)."""

    try:
        await search_client.get_document_count()
        search_reachable = True
    except Exception as e:
        logger.exception("Error while checking connection to the search service", {"error": str(e)})
        search_reachable = False

    # TODO: Add health check for openai service in a later PR
    openai_reachable = True

    healthy = search_reachable and openai_reachable

    response = HealthStatusResponse(healthy=healthy, status=None)
    if config.health_secret != "" and API_KEY_HEADER in request.headers and request.headers[API_KEY_HEADER] == config.health_secret:
        response.status = HealthDetailedStatus(
            status_openai=True,
            status_search=search_reachable,
            budget=0,
        )

    return (
        jsonify(
            response.model_dump(
                exclude_none=True,
            )
        ),
        200 if healthy else 500,
    )
