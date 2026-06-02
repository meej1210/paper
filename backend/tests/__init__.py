import pytest
from app import create_app
from app.extensions import db as _db
from app.models import User


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def sample_user(app, db):
    from app.utils.security import hash_password

    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("password123"),
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def admin_user(app, db):
    from app.utils.security import hash_password
    from app.models import UserRole

    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("adminpass123"),
        role=UserRole.ADMIN,
    )
    db.session.add(user)
    db.session.commit()
    return user


def auth_headers(user_id: int) -> dict:
    from flask_jwt_extended import create_access_token

    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_headers(sample_user):
    return auth_headers(sample_user.id)


@pytest.fixture()
def admin_headers(admin_user):
    return auth_headers(admin_user.id)
