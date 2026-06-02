import time

from app import create_app
from app.extensions import db
from app.models import TaskType, User
from app.services.task_service import create_task
from app.utils.security import hash_password

stamp = int(time.time())
username = f"cancel{stamp}"
email = f"{username}@example.com"

app = create_app()
client = app.test_client()

with app.app_context():
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, email=email, password_hash=hash_password("StrongPass123"), is_active=True)
        db.session.add(user)
    db.session.commit()

login = client.post("/api/auth/login", json={"username": username, "password": "StrongPass123"})
if login.status_code != 200:
    raise RuntimeError(f"login failed: {login.status_code} {login.json}")
headers = {"Authorization": f"Bearer {login.json['data']['access_token']}"}

with app.app_context():
    user = User.query.filter_by(username=username).first()
    task = create_task(user_id=user.id, task_type=TaskType.DAST, task_name="cancel-test", target_url="http://example.com", timeout_seconds=60)
    task_id = task.id

cancel = client.post(f"/api/tasks/{task_id}/cancel", headers=headers)
print("cancel", cancel.status_code, cancel.json)

detail = client.get("/api/tasks", headers=headers)
print("list", detail.status_code, detail.json)
