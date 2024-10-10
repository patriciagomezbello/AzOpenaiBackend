import os

from api.errors import ErrorProvider
from api.routes import api_bp
from azure.monitor.opentelemetry import configure_azure_monitor
from config import Config
from containers import DIContainer
from dependency_injector.wiring import inject
from dependency_injector.wiring import Provide
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from quart import Quart
from quart import ResponseReturnValue
from quart_cors import cors
from quart_schema import Info
from quart_schema import QuartSchema
from services.logger import new_logger
from werkzeug.exceptions import HTTPException

logger = new_logger(__name__)

API_VERSION = "2.1.1"


@inject
def new_app(
    config: Config = Provide[DIContainer.settings],
) -> tuple[Quart, QuartSchema]:
    """Create and configure an instance of the Quart application."""
    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        configure_azure_monitor()
        AioHttpClientInstrumentor().instrument()
        LoggingInstrumentor().instrument()
        RequestsInstrumentor().instrument()

    app = Quart(__name__)
    app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)  # type: ignore

    logger.info("Initializing server")

    blueprint = api_bp
    # TODO: Move to config
    if os.getenv("CORS_DISABLED", "false").lower() == "true":
        logger.warning("CORS middleware is disabled.")
        blueprint = cors(blueprint, allow_origin="*")
    app.register_blueprint(blueprint, url_prefix=config.api_path)

    return app, QuartSchema(
        app,
        info=Info(title="Telekom LLM & CompanyData API", version=API_VERSION),
        openapi_path=os.path.join(config.api_path, "openapi.json"),
        swagger_ui_path=os.path.join(config.api_path, "docs"),
        redoc_ui_path=os.path.join(config.api_path, "redocs"),
        security=[{"bearerAuth": []}],
        security_schemes={"bearerAuth": {"type": "http", "bearer_format": "JWT", "scheme": "bearer"}},
    )


di_container = DIContainer()
# We need to wire up the inject decorator to access the DI Container
di_container.wire(modules=[__name__], packages=["api"])


app, schema = new_app()


@app.before_serving
async def startup() -> None:
    await di_container.init_resources()  # type: ignore because coroutine detection does not work


@app.errorhandler(Exception)
async def handle_error(error: Exception) -> HTTPException | ResponseReturnValue:
    if isinstance(error, HTTPException):
        return error

    logger.exception("An error occurred while processing the request", {"error": str(error)})
    return ErrorProvider.error_response("error occurred while processing the request", 500, error=error)


@app.after_serving
async def shutdown() -> None:
    try:
        await di_container.shutdown_resources()  # type: ignore because coroutine detection does not work
    except Exception as e:
        logger.error("Error while shutting down resources", {"error": str(e)})
