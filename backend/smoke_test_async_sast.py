import io
import os
import time

os.environ["CELERY_TASK_ALWAYS_EAGER"] = "false"

from app import create_app

stamp = int(time.time())
username = f"asyncsast{stamp}"
email = f"{username}@example.com"
sample_code = b"import subprocess\nsubprocess.Popen('ls', shell=True)\n"

app = create_app()
client = app.test_client()

client.post("/api/auth/register", json={"username": username, "email": email, "password": "StrongPass123"})
login = client.post("/api/auth/login", json={"username": username, "password": "StrongPass123"})
headers = {"Authorization": f"Bearer {login.json['data']['access_token']}"}

create_resp = client.post(
    "/api/sast/tasks",
    data={
        "file": (io.BytesIO(sample_code), "async_vuln.py"),
        "task_name": "async-sast"
    },
    headers=headers,
    content_type="multipart/form-data",
)
print("create", create_resp.status_code, create_resp.json)

task_id = create_resp.json["data"]["task"]["id"]

for idx in range(12):
    time.sleep(1)
    detail = client.get(f"/api/sast/tasks/{task_id}", headers=headers)
    payload = detail.json
    status = payload["data"]["task"]["status"]
    print("poll", idx + 1, status, payload)
    if status in {"SUCCESS", "FAILED", "TIMEOUT", "CANCELLED"}:
        break
