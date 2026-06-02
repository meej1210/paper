from app import create_app
from app.extensions import db
import os

from app.models import AuditLog, DastResult, SastResult, Task, User
from app.services.auth_service import ensure_admin_user

app = create_app()

with app.app_context():
    db.create_all()
    admin = ensure_admin_user(
        os.getenv("ADMIN_USERNAME", "admin"),
        os.getenv("ADMIN_EMAIL", "admin@example.com"),
        os.getenv("ADMIN_PASSWORD", "adminpass123"),
    )
    print("database initialized")
    print(app.config["SQLALCHEMY_DATABASE_URI"])
    print(f"admin user ready: {admin.username} ({admin.email})")
