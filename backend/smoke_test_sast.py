import io
import os
import time

os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from app import create_app

stamp = int(time.time())
username = f"sast{stamp}"
email = f"{username}@example.com"

sample_code = b"import subprocess\nsubprocess.Popen('ls', shell=True)\n"

app = create_app()
client = app.test_client()

client.post(
    "/api/auth/register",
    json={"username": username, "email": email, "password": "StrongPass123"},
)
login = client.post(
    "/api/auth/login",
    json={"username": username, "password": "StrongPass123"},
)
headers = {"Authorization": f"Bearer {login.json['data']['access_token']}"}

payload = {
    "file": (io.BytesIO(sample_code), "vuln.py"),
    "task_name": "demo-sast",
    "description": "smoke test",
}
response = client.post("/api/sast/tasks", data=payload, headers=headers, content_type="multipart/form-data")
print("sast", response.status_code, response.json)

if response.status_code == 201:
    task_id = response.json["data"]["task"]["id"]
    detail = client.get(f"/api/sast/tasks/{task_id}", headers=headers)
    print("sast-detail", detail.status_code, detail.json)
