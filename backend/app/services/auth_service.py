from flask_jwt_extended import create_access_token
from sqlalchemy import or_

from ..extensions import db
from ..models import User, UserRole
from ..utils.exceptions import ApiError
from ..utils.security import hash_password, verify_password


def register_user(username: str, email: str, password: str) -> User:
    if User.query.filter_by(username=username).first():
        raise ApiError("username already exists", code=40900, status_code=409, errors={"username": "already exists"})
    if User.query.filter_by(email=email).first():
        raise ApiError("email already exists", code=40900, status_code=409, errors={"email": "already exists"})

    user = User(username=username, email=email, password_hash=hash_password(password), role=UserRole.USER)
    db.session.add(user)
    db.session.commit()
    return user


def ensure_admin_user(username: str, email: str, password: str) -> User:
    existing = User.query.filter(or_(User.username == username, User.email == email)).first()
    if existing:
        existing.username = username
        existing.email = email
        existing.password_hash = hash_password(password)
        existing.role = UserRole.ADMIN
        existing.is_active = True
        db.session.commit()
        return existing

    user = User(username=username, email=email, password_hash=hash_password(password), role=UserRole.ADMIN)
    db.session.add(user)
    db.session.commit()
    return user


def login_user(username: str, password: str):
    user = User.query.filter(or_(User.username == username, User.email == username)).first()
    if not user or not verify_password(password, user.password_hash):
        raise ApiError("unauthorized", code=40100, status_code=401)
    if not user.is_active:
        raise ApiError("permission denied", code=40300, status_code=403)

    token = create_access_token(identity=str(user.id))
    return token, user
