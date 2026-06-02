import os
import time

os.environ["CELERY_TASK_ALWAYS_EAGER"] = "false"

from app import create_app
from app.extensions import db
from app.models import User
from app.utils.security import hash_password

stamp = int(time.time())
username = f"async{stamp}"
email = f"{username}@example.com"

app = create_app()
client = app.test_client()

with app.app_context():
    user = User.query.filter_by(username=username).first()
    if not user:
        db.session.add(User(username=username, email=email, password_hash=hash_password("StrongPass123"), is_active=True))
    db.session.commit()

login = client.post("/api/auth/login", json={"username": username, "password": "StrongPass123"})
if login.status_code != 200:
    raise RuntimeError(f"login failed: {login.status_code} {login.json}")
headers = {"Authorization": f"Bearer {login.json['data']['access_token']}"}

create_resp = client.post(
    "/api/dast/tasks",
    json={"target_url": "http://example.com", "task_name": "async-dast", "timeout": 5, "authorization_confirmed": True},
    headers=headers,
)
print("create", create_resp.status_code, create_resp.json)
if create_resp.status_code != 201:
    raise RuntimeError(f"create failed: {create_resp.status_code} {create_resp.json}")

task_id = create_resp.json["data"]["task"]["id"]

for idx in range(10):
    time.sleep(1)
    detail = client.get(f"/api/dast/tasks/{task_id}", headers=headers)
    payload = detail.json
    status = payload["data"]["task"]["status"]
    print("poll", idx + 1, status, payload)
    if status in {"SUCCESS", "FAILED", "TIMEOUT", "CANCELLED"}:
        break
