from pathlib import Path

import redis
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(get_remote_address, default_limits=["200 per minute"], storage_uri="memory://")

_redis_pool: redis.ConnectionPool | None = None


def get_redis_client(config: dict) -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(config["REDIS_URL"])
    return redis.Redis(connection_pool=_redis_pool)


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": [app.config["FRONTEND_ORIGIN"], "*"]}})

    storage_uri = app.config.get("RATELIMIT_STORAGE_URI", app.config["REDIS_URL"])
    limiter._storage_uri = storage_uri
    limiter.init_app(app)

    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["REPORT_DIR"]).mkdir(parents=True, exist_ok=True)
