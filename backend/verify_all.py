import io
import os
import time

os.environ["CELERY_TASK_ALWAYS_EAGER"] = "false"

from app import create_app
from app.extensions import db
from app.models import User
from app.utils.security import hash_password


LOCAL_DAST_TARGET = os.getenv("VERIFY_DAST_TARGET", "http://127.0.0.1:5000/")


def wait_for_final_status(client, path, headers, timeout=20):
    for _ in range(timeout):
        time.sleep(1)
        resp = client.get(path, headers=headers)
        data = resp.json["data"]
        status = data["task"]["status"]
        if status in {"SUCCESS", "FAILED", "TIMEOUT", "CANCELLED"}:
            return resp
    return resp


stamp = int(time.time())
username = f"verifyall{stamp}"
email = f"{username}@example.com"
app = create_app()
client = app.test_client()

health = client.get("/api/health")
print("[health]", health.status_code, health.json)

with app.app_context():
    user = User.query.filter_by(username=username).first()
    if not user:
        db.session.add(User(username=username, email=email, password_hash=hash_password("StrongPass123"), is_active=True))
    db.session.commit()
print("[user-ready]", username)

login = client.post("/api/auth/login", json={"username": username, "password": "StrongPass123"})
print("[login]", login.status_code)
if login.status_code != 200:
    raise RuntimeError(f"login failed: {login.status_code} {login.json}")
headers = {"Authorization": f"Bearer {login.json['data']['access_token']}"}

me = client.get("/api/auth/me", headers=headers)
print("[me]", me.status_code, me.json)

dast_create = client.post(
    "/api/dast/tasks",
    json={"target_url": LOCAL_DAST_TARGET, "task_name": "verify-dast", "timeout": 20, "authorization_confirmed": True},
    headers=headers,
)
print("[dast-create]", dast_create.status_code, dast_create.json)
if dast_create.status_code != 201:
    raise RuntimeError(f"dast create failed: {dast_create.status_code} {dast_create.json}")
dast_id = dast_create.json["data"]["task"]["id"]
dast_final = wait_for_final_status(client, f"/api/dast/tasks/{dast_id}", headers, timeout=40)
print("[dast-final]", dast_final.status_code, dast_final.json)

sample_code = b"import subprocess\nsubprocess.Popen('ls', shell=True)\n"
sast_create = client.post(
    "/api/sast/tasks",
    data={"file": (io.BytesIO(sample_code), "verify_async.py"), "task_name": "verify-sast"},
    headers=headers,
    content_type="multipart/form-data",
)
print("[sast-create]", sast_create.status_code, sast_create.json)
sast_id = sast_create.json["data"]["task"]["id"]
sast_final = wait_for_final_status(client, f"/api/sast/tasks/{sast_id}", headers)
print("[sast-final]", sast_final.status_code, sast_final.json)

report = client.get(f"/api/sast/tasks/{sast_id}/report", headers=headers)
print("[report]", report.status_code, report.headers.get("Content-Type"), len(report.data))

tasks = client.get("/api/tasks", headers=headers)
print("[tasks]", tasks.status_code, tasks.json)
