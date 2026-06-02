import os
import time

os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from app import create_app

stamp = int(time.time())
username = f"admin{stamp}"
email = f"{username}@example.com"

app = create_app()
client = app.test_client()

health = client.get("/api/health")
print("health", health.status_code, health.json)

register = client.post(
    "/api/auth/register",
    json={"username": username, "email": email, "password": "StrongPass123"},
)
print("register", register.status_code, register.json)

login = client.post(
    "/api/auth/login",
    json={"username": username, "password": "StrongPass123"},
)
print("login", login.status_code, login.json)

token = login.json["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

me = client.get("/api/auth/me", headers=headers)
print("me", me.status_code, me.json)

listing = client.get("/api/tasks", headers=headers)
print("tasks", listing.status_code, listing.json)

dast = client.post(
    "/api/dast/tasks",
    json={"target_url": "http://example.com", "task_name": "demo-dast", "timeout": 2},
    headers=headers,
)
print("dast", dast.status_code, dast.json)

if dast.status_code == 201:
    task_id = dast.json["data"]["task"]["id"]
    detail = client.get(f"/api/dast/tasks/{task_id}", headers=headers)
    print("dast-detail", detail.status_code, detail.json)
