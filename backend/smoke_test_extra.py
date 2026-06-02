import io
import os
import time

os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from app import create_app

stamp = int(time.time())
username = f"verify{stamp}"
email = f"{username}@example.com"

sample_code = b"import subprocess\nsubprocess.Popen('ls', shell=True)\n"

app = create_app()
client = app.test_client()

client.post("/api/auth/register", json={"username": username, "email": email, "password": "StrongPass123"})
login = client.post("/api/auth/login", json={"username": username, "password": "StrongPass123"})
headers = {"Authorization": f"Bearer {login.json['data']['access_token']}"}

sast = client.post(
    "/api/sast/tasks",
    data={
        "file": (io.BytesIO(sample_code), "verify.py"),
        "task_name": "verify-sast"
    },
    headers=headers,
    content_type="multipart/form-data",
)
print("sast", sast.status_code)

task_id = sast.json["data"]["task"]["id"]
report = client.get(f"/api/sast/tasks/{task_id}/report", headers=headers)
print("report", report.status_code, report.headers.get("Content-Type"), len(report.data))

rerun = client.post(f"/api/tasks/{task_id}/rerun", headers=headers)
print("rerun", rerun.status_code, rerun.json)

listing = client.get("/api/tasks", headers=headers)
print("task-count", listing.json["data"]["pagination"]["total"])
