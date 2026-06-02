from flask import Flask
from werkzeug.exceptions import HTTPException

from .ai import ai_bp
from .admin import admin_bp
from .audit import audit_bp
from .auth import auth_bp
from .dast import dast_bp
from .health import health_bp
from .metrics import metrics_bp
from .sca import sca_bp
from .sast import sast_bp
from .tasks import tasks_bp
from ..utils.exceptions import ApiError
from ..utils.response import error_response


def register_blueprints(app: Flask):
    app.register_blueprint(ai_bp, url_prefix="/api/ai")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(metrics_bp, url_prefix="/api/metrics")
    app.register_blueprint(sast_bp, url_prefix="/api/sast")
    app.register_blueprint(dast_bp, url_prefix="/api/dast")
    app.register_blueprint(sca_bp, url_prefix="/api/sca")
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
    app.register_blueprint(audit_bp, url_prefix="/api/audit-logs")

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return error_response(error.code, error.message, error.errors, error.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        return error_response(error.code * 100, error.description, status_code=error.code)

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        return error_response(50000, "internal server error", errors={"detail": str(error)}, status_code=500)
