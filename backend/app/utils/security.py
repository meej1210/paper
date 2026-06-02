from functools import wraps

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from werkzeug.security import check_password_hash, generate_password_hash

from ..models import User, UserRole
from .exceptions import ApiError

from ..extensions import db as _db


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def current_user():
    user_id = get_jwt_identity()
    user = _db.session.get(User, int(user_id))
    if not user:
        raise ApiError("user not found", code=40400, status_code=404)
    return user


def require_roles(*roles: UserRole):
    allowed = {role.value if isinstance(role, UserRole) else role for role in roles}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if user.role.value not in allowed:
                raise ApiError("permission denied", code=40300, status_code=403)
            return func(*args, **kwargs)

        return wrapper

    return decorator
