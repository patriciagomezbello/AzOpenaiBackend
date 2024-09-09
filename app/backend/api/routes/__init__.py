from api.routes.health import health_bp
from api.routes.legacy import legacy_bp
from api.routes.openapi import openapi_bp
from api.routes.v1 import v1_bp
from quart import Blueprint

api_bp = Blueprint("api", __name__)
api_bp.register_blueprint(health_bp)
api_bp.register_blueprint(openapi_bp)
api_bp.register_blueprint(legacy_bp)
api_bp.register_blueprint(v1_bp)
