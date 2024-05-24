from api import create_server
from config import Config
from quart import Quart


def create_app() -> Quart:
    """Create and configure an instance of the Quart application."""
    config = Config.load_config()

    app = create_server(config)
    return app
