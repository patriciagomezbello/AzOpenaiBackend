from typing import Any

import yaml
from quart import Blueprint
from quart import make_response
from quart.typing import ResponseTypes
from quart_schema import hide
from quart_schema.extension import _build_openapi_schema
from services.logger import new_logger

logger = new_logger(__name__)
openapi_bp = Blueprint("openapi", __name__)


# TODO: remove this route as soon as https://github.com/pgjones/quart-schema/issues/79 is implemented
# and the openapi.yaml route is part of the quart-schema package
@hide
@openapi_bp.route("/openapi.yaml")
@openapi_bp.route("/openapi.yml")
async def openapi_yaml() -> ResponseTypes:
    """openapi_yaml returns the openapi schema as a yaml string."""
    from main import app
    from main import schema

    openapi_schema: dict[str, Any] = _build_openapi_schema(app, schema)
    schema_yaml = yaml.dump(openapi_schema, indent=2)
    response = await make_response(schema_yaml)
    response.headers["Content-Type"] = "text/yaml"
    response.headers["Content-Disposition"] = "inline"
    return response
