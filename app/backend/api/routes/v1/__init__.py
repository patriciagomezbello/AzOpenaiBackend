from api.routes.legacy.category import bp as legacy_category_blueprint
from api.routes.legacy.chat import bp as legacy_chat_blueprint
from api.routes.legacy.content import bp as legacy_content_blueprint
from api.routes.legacy.feedback import bp as legacy_feedback_blueprint
from api.routes.legacy.prompt import bp as legacy_prompts_blueprint
from quart import Blueprint

v1_bp = Blueprint("v1", __name__, url_prefix="/v1")
v1_bp.register_blueprint(legacy_feedback_blueprint)
v1_bp.register_blueprint(legacy_content_blueprint)
v1_bp.register_blueprint(legacy_category_blueprint)
v1_bp.register_blueprint(legacy_chat_blueprint)
v1_bp.register_blueprint(legacy_prompts_blueprint)
