import shutil

from flask import Blueprint, current_app

from ..extensions import db, get_redis_client
from ..utils.response import success_response


health_bp = Blueprint("health", __name__)


@health_bp.get("")
def health_check():
    db_status = "up"
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    redis_status = "down"
    try:
        client = get_redis_client(current_app.config)
        if client.ping():
            redis_status = "up"
    except Exception:
        redis_status = "down"

    scanner_status = "up" if shutil.which(current_app.config["DAST_SCANNER_CMD"]) else "down"

    return success_response(
        {
            "service": "up",
            "database": db_status,
            "redis": redis_status,
            "dast_scanner": scanner_status,
            "celery_mode": "eager" if current_app.config.get("CELERY_TASK_ALWAYS_EAGER") else "async",
        }
    )
