from api.routes.legacy.category import bp as legacy_category_blueprint
from api.routes.legacy.chat import bp as legacy_chat_blueprint
from api.routes.legacy.content import bp as legacy_content_blueprint
from api.routes.legacy.feedback import bp as legacy_feedback_blueprint
from api.routes.legacy.prompt import bp as legacy_prompt_blueprint
from quart import Blueprint

legacy_bp = Blueprint("legacy", __name__)
legacy_bp.register_blueprint(legacy_feedback_blueprint)
legacy_bp.register_blueprint(legacy_content_blueprint)
legacy_bp.register_blueprint(legacy_category_blueprint)
legacy_bp.register_blueprint(legacy_chat_blueprint)
legacy_bp.register_blueprint(legacy_prompt_blueprint)
