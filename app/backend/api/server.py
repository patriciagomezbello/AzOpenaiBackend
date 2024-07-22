import asyncio
import os
import platform
from typing import Any
from typing import Dict

import yaml
from api.controllers import Controllers
from api.controllers.category import CategoryRoute
from api.controllers.chat import ChatRoute
from api.controllers.content import ContentRoute
from api.controllers.feedback import FeedbackRoute
from azure.monitor.opentelemetry import configure_azure_monitor
from clients.factory import initialize_clients
from config import Config
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from quart import Blueprint
from quart import make_response
from quart import Quart
from quart.typing import ResponseTypes
from quart_cors import cors
from quart_schema import hide
from quart_schema import Info
from quart_schema import QuartSchema
from quart_schema.extension import _build_openapi_schema
from services.factory import ServiceFactory
from services.logger import new_logger


__all__ = ["Server"]


logger = new_logger(__name__)


class Server:
    """Server is a class that holds the API and its routes."""

    # API_VERSION is the version of the Servers API.
    API_VERSION = "v1.0.0"

    def __init__(self, cfg: Config):
        self.api_path = cfg.api_path
        self.clients: Dict[str, Any] = initialize_clients(cfg)
        self.svc_factory = ServiceFactory(cfg, self.clients)
        self.controllers = Controllers(cfg, self.svc_factory)

    async def initialize(self) -> Quart:
        """initialize initializes the Quart app."""

        self.bp: Blueprint = Blueprint("routes", __name__)
        if platform.system() == "Darwin" or os.getenv("CORS_DISABLED", "false").lower() == "true":
            logger.warning("CORS middleware is disabled.")
            self.bp = cors(self.bp, allow_origin="*")

        self._register_routes()
        self.bp.before_app_serving(self.controllers.startup)
        self.bp.after_app_serving(self.shutdown)
        self.app = self._create_app()

        return self.app

    def _register_routes(self):
        """_register_routes registers all the routes for the API."""

        self.bp.url_prefix = self._get_url_prefix()

        self.bp.add_url_rule("/openapi.yaml", view_func=self.openapi_yaml)

        category_view = CategoryRoute.as_view("category_api", category_controller=self.controllers.category)
        self.bp.add_url_rule("/categories", view_func=category_view, methods=["GET"])

        chat_view = ChatRoute.as_view("chat_api", chat_controller=self.controllers.chat)
        self.bp.add_url_rule("/chat", view_func=chat_view, methods=["POST"])

        content_view = ContentRoute.as_view("content_api", content_controller=self.controllers.content)
        self.bp.add_url_rule("/content/<path>", view_func=content_view, methods=["GET"])

        feedback_view = FeedbackRoute.as_view("feedback_api", feedback_controller=self.controllers.feedback)
        self.bp.add_url_rule("/feedback", view_func=feedback_view, methods=["POST"])

    def _create_app(self) -> Quart:
        """_create_app creates the Quart app and registers the blueprint."""

        if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
            configure_azure_monitor()
            AioHttpClientInstrumentor().instrument()
            LoggingInstrumentor().instrument()
            RequestsInstrumentor().instrument()
        app = Quart(__name__)
        app.register_blueprint(self.bp)
        app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)  # type: ignore
        prefix = self._get_url_prefix()
        self.schema = QuartSchema(
            app,
            info=Info(title="Telekom LLM & CompanyData API", version=self.API_VERSION),
            openapi_path=os.path.join(prefix, "openapi.json"),
            swagger_ui_path=os.path.join(prefix, "docs"),
            redoc_ui_path=os.path.join(prefix, "redocs"),
            security=[{"bearerAuth": []}],
            security_schemes={"bearerAuth": {"type": "http", "bearer_format": "JWT", "scheme": "bearer"}},
        )
        return app

    # TODO: remove this route as soon as https://github.com/pgjones/quart-schema/issues/79 is implemented
    # and the openapi.yaml route is part of the quart-schema package
    @hide
    async def openapi_yaml(self) -> ResponseTypes:
        """openapi_yaml returns the openapi schema as a yaml string."""
        schema: dict[str, Any] = _build_openapi_schema(self.app, self.schema)
        # We need to remove the "v" prefix from the version to match the openapi spec.
        # https://swagger.io/specification/#info-object
        schema["info"]["version"] = self.API_VERSION.removeprefix("v")
        schema_yaml = yaml.dump(schema, indent=2)
        response = await make_response(schema_yaml)
        response.headers["Content-Type"] = "text/yaml"
        response.headers["Content-Disposition"] = "inline"
        return response

    async def shutdown(self) -> None:
        """shutdown closes all the clients."""
        for client in self.clients.values():
            await client.close()

    def _get_url_prefix(self) -> str:
        """_get_url_prefix returns the url prefix for the API."""
        if self.api_path != "/":
            return os.path.join(self.api_path, self.API_VERSION.split(".")[0])
        return self.api_path


def create_server(cfg: Config) -> Quart:
    """create_app creates the Quart app."""
    server = Server(cfg)
    logger.info("Initializing server")
    app = asyncio.run(server.initialize())
    return app
