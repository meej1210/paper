from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..extensions import limiter
from ..services.audit_service import log_action
from ..services.auth_service import login_user, register_user
from ..utils.exceptions import ApiError
from ..utils.response import success_response
from ..utils.security import current_user
from ..utils.validators import validate_login_payload, validate_register_payload


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    payload = request.get_json(silent=True) or {}
    validate_register_payload(payload)
    user = register_user(payload["username"], payload["email"], payload["password"])
    log_action("REGISTER", user_id=user.id, resource_type="user", resource_id=user.id, detail={"username": user.username, "result": "success"}, request=request)
    return success_response({"user": user.to_dict()}, message="register success", status_code=201)


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    payload = request.get_json(silent=True) or {}
    validate_login_payload(payload)
    username = payload["username"]
    try:
        token, user = login_user(username, payload["password"])
    except ApiError:
        log_action(
            "AUTH_LOGIN_FAILED",
            resource_type="user",
            detail={"username": username, "result": "failed", "reason": "invalid_credentials"},
            request=request,
        )
        raise
    log_action(
        "AUTH_LOGIN_SUCCESS",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        detail={"username": user.username, "result": "success"},
        request=request,
    )
    return success_response({"access_token": token, "token_type": "Bearer", "user": user.to_dict()}, message="login success")


@auth_bp.get("/me")
@jwt_required()
def me():
    return success_response({"user": current_user().to_dict()})
