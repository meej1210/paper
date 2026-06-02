import io
import time
import requests

stamp = int(time.time())
username = f"http_sast_{stamp}"
email = f"{username}@example.com"
base = "http://127.0.0.1:5000/api"

r = requests.post(f"{base}/auth/register", json={"username": username, "email": email, "password": "StrongPass123"})
print("register", r.status_code, r.json())

r = requests.post(f"{base}/auth/login", json={"username": username, "password": "StrongPass123"})
print("login", r.status_code, r.json())
token = r.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

files = {"file": ("http_test.py", io.BytesIO(b"import subprocess\nsubprocess.Popen('ls', shell=True)\n"), "text/x-python")}
data = {"task_name": "http-sast", "description": "http upload test"}
r = requests.post(f"{base}/sast/tasks", headers=headers, files=files, data=data)
print("create", r.status_code, r.json())

task_id = r.json()["data"]["task"]["id"]
for idx in range(10):
    time.sleep(1)
    detail = requests.get(f"{base}/sast/tasks/{task_id}", headers=headers)
    payload = detail.json()
    print("poll", idx + 1, payload)
    if payload["data"]["task"]["status"] in {"SUCCESS", "FAILED", "TIMEOUT", "CANCELLED"}:
        break
