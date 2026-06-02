import pytest
from werkzeug.exceptions import TooManyRequests

from tests.conftest import _auth_headers as auth_headers


class TestRegister:
    def test_http_exception_keeps_status_code(self, app, client):
        @app.get("/raise-too-many-requests")
        def raise_too_many_requests():
            raise TooManyRequests("rate limit exceeded")

        response = client.get("/raise-too-many-requests")

        assert response.status_code == 429
        assert response.get_json()["message"] == "rate limit exceeded"

    def test_register_success(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "new@example.com", "password": "password123"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["data"]["user"]["username"] == "newuser"
        assert data["data"]["user"]["role"] == "user"
        assert "password" not in data["data"]["user"]
        assert "password_hash" not in data["data"]["user"]

    def test_register_missing_fields(self, client):
        response = client.post("/api/auth/register", json={"username": "x"})
        assert response.status_code == 400
        data = response.get_json()
        assert "email" in data.get("errors", {})
        assert "password" in data.get("errors", {})

    def test_register_short_password(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "shortpw", "email": "s@example.com", "password": "1234567"},
        )
        assert response.status_code == 400

    def test_register_duplicate_username(self, client, sample_user):
        response = client.post(
            "/api/auth/register",
            json={"username": "testuser", "email": "other@example.com", "password": "password123"},
        )
        assert response.status_code == 409

    def test_register_invalid_email(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "bademail", "email": "not-an-email", "password": "password123"},
        )
        assert response.status_code == 400


class TestLogin:
    def test_login_success(self, client, sample_user):
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data["data"]
        assert data["data"]["user"]["username"] == "testuser"

    def test_login_wrong_password(self, client, sample_user):
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "password123"},
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 400


class TestGetCurrentUser:
    def test_me_success(self, client, sample_user):
        response = client.get("/api/auth/me", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["user"]["username"] == "testuser"

    def test_me_no_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code in (401, 422)


class TestAdminBootstrap:
    def test_ensure_admin_user_creates_admin_from_values(self, app, db):
        from app.models import User, UserRole
        from app.services.auth_service import ensure_admin_user
        from app.utils.security import verify_password

        admin = ensure_admin_user("root", "root@example.com", "adminpass123")

        assert admin.username == "root"
        assert admin.email == "root@example.com"
        assert admin.role == UserRole.ADMIN
        assert verify_password("adminpass123", admin.password_hash)
        assert User.query.filter_by(role=UserRole.ADMIN).count() == 1

    def test_ensure_admin_user_creates_named_admin_when_another_admin_exists(self, app, db, admin_user):
        from app.models import User, UserRole
        from app.services.auth_service import ensure_admin_user
        from app.utils.security import verify_password

        admin = ensure_admin_user("newadmin", "newadmin@example.com", "newpass123")

        assert admin.id != admin_user.id
        assert admin.username == "newadmin"
        assert admin.email == "newadmin@example.com"
        assert admin.role == UserRole.ADMIN
        assert verify_password("newpass123", admin.password_hash)
        assert User.query.filter_by(role=UserRole.ADMIN).count() == 2

    def test_ensure_admin_user_refreshes_existing_named_admin(self, app, db, admin_user):
        from app.models import User, UserRole
        from app.services.auth_service import ensure_admin_user
        from app.utils.security import verify_password

        admin = ensure_admin_user("admin", "admin@example.com", "newpass123")

        assert admin.id == admin_user.id
        assert admin.role == UserRole.ADMIN
        assert admin.is_active is True
        assert verify_password("newpass123", admin.password_hash)
