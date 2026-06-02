from flask import Flask

from .api import register_blueprints
from .config import get_config
from .extensions import init_extensions


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    init_extensions(app)
    register_blueprints(app)

    return app
