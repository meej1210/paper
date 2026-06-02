import time

from app import create_app
from app.extensions import db
from app.models import User, UserRole
from app.utils.security import hash_password

stamp = int(time.time())
username = f"audit{stamp}"
email = f"{username}@example.com"

app = create_app()
client = app.test_client()

with app.app_context():
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, email=email, password_hash=hash_password("StrongPass123"), is_active=True)
        db.session.add(user)
    user.role = UserRole.ADMIN
    db.session.commit()

login = client.post("/api/auth/login", json={"username": username, "password": "StrongPass123"})
if login.status_code != 200:
    raise RuntimeError(f"login failed: {login.status_code} {login.json}")
headers = {"Authorization": f"Bearer {login.json['data']['access_token']}"}

logs = client.get("/api/audit-logs", headers=headers)
print("audit", logs.status_code)
print(logs.json)
