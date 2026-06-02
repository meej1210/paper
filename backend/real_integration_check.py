import os
import sys
import time
from pathlib import Path

import requests

from app import create_app
from app.extensions import db
from app.models import User, UserRole
from app.utils.security import hash_password

BASE_URL = os.getenv("VERIFY_BASE_URL", "http://127.0.0.1:5000/api")
DAST_TARGET = os.getenv("VERIFY_DAST_TARGET", "http://127.0.0.1:3100")
ADMIN_USERNAME = os.getenv("VERIFY_ADMIN_USERNAME", "integration_admin")
ADMIN_EMAIL = os.getenv("VERIFY_ADMIN_EMAIL", "integration_admin@example.com")
ADMIN_PASSWORD = os.getenv("VERIFY_ADMIN_PASSWORD", "StrongPass123")
USER_PASSWORD = "StrongPass123"
TIMEOUT = 15

ROOT_DIR = Path(__file__).resolve().parent.parent
SAST_FILE = ROOT_DIR / "tests" / "dangerous_ops.py"


def ensure_admin_user() -> None:
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=ADMIN_USERNAME).first()
        if not user:
            user = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.session.add(user)
        else:
            user.email = ADMIN_EMAIL
            user.password_hash = hash_password(ADMIN_PASSWORD)
            user.role = UserRole.ADMIN
            user.is_active = True
        db.session.commit()


def ensure_regular_user(username: str, email: str, password: str) -> dict:
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.USER,
                is_active=True,
            )
            db.session.add(user)
        else:
            user.email = email
            user.password_hash = hash_password(password)
            user.role = UserRole.USER
            user.is_active = True
        db.session.commit()
        return user.to_dict()


def request_json(method: str, path: str, *, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
    return response


def assert_ok(response, label: str):
    if response.status_code >= 400:
        raise RuntimeError(f"{label} failed: {response.status_code} {response.text[:500]}")
    return response


def login(username: str, password: str) -> str:
    response = assert_ok(
        request_json("POST", "/auth/login", json={"username": username, "password": password}),
        f"login {username}",
    )
    payload = response.json()
    return payload["data"]["access_token"]


def wait_for_task(path: str, token: str, timeout_seconds: int = 180):
    last_payload = None
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = assert_ok(request_json("GET", path, token=token), f"poll {path}")
        last_payload = response.json()["data"]
        status = last_payload["task"]["status"]
        if status in {"SUCCESS", "FAILED", "TIMEOUT", "CANCELLED"}:
            return last_payload
        time.sleep(3)
    raise TimeoutError(f"task did not finish in time: {path} last={last_payload}")


def main():
    ensure_admin_user()

    health = assert_ok(request_json("GET", "/health"), "health").json()
    health_data = health["data"]

    admin_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)

    stamp = int(time.time())
    username = f"integration_{stamp}"
    email = f"{username}@example.com"

    registered_user = ensure_regular_user(username, email, USER_PASSWORD)

    user_token = login(username, USER_PASSWORD)

    with SAST_FILE.open("rb") as fh:
        sast_create = assert_ok(
            request_json(
                "POST",
                "/sast/tasks",
                token=user_token,
                data={"task_name": "integration-sast", "description": "real integration sast run"},
                files={"file": (SAST_FILE.name, fh, "text/x-python")},
            ),
            "create sast",
        ).json()
    sast_id = sast_create["data"]["task"]["id"]
    sast_final = wait_for_task(f"/sast/tasks/{sast_id}", user_token)

    sast_report = assert_ok(request_json("GET", f"/sast/tasks/{sast_id}/report", token=user_token), "download sast report")
    sast_html = assert_ok(request_json("GET", f"/sast/tasks/{sast_id}/export?format=html", token=user_token), "export sast html")
    sast_pdf = request_json("GET", f"/sast/tasks/{sast_id}/export?format=pdf", token=user_token)

    dast_create = assert_ok(
        request_json(
            "POST",
            "/dast/tasks",
            token=user_token,
            json={
                "target_url": DAST_TARGET,
                "task_name": "integration-dast",
                "description": "real integration dast run",
                "timeout": 60,
                "authorization_confirmed": True,
            },
        ),
        "create dast",
    ).json()
    dast_id = dast_create["data"]["task"]["id"]
    dast_final = wait_for_task(f"/dast/tasks/{dast_id}", user_token, timeout_seconds=240)

    dast_report = assert_ok(request_json("GET", f"/dast/tasks/{dast_id}/report", token=user_token), "download dast report")
    dast_html = assert_ok(request_json("GET", f"/dast/tasks/{dast_id}/export?format=html", token=user_token), "export dast html")
    dast_pdf = request_json("GET", f"/dast/tasks/{dast_id}/export?format=pdf", token=user_token)

    audit_logs = assert_ok(
        request_json("GET", f"/audit-logs?page=1&page_size=20&action=TASK_CREATE", token=admin_token),
        "audit logs",
    ).json()

    print("HEALTH", health_data)
    print("REGISTERED_USER", registered_user)
    print(
        "SAST",
        {
            "task_id": sast_id,
            "status": sast_final["task"]["status"],
            "issue_count": (sast_final.get("result") or {}).get("issue_count"),
            "report_bytes": len(sast_report.content),
            "html_bytes": len(sast_html.content),
            "pdf_status": sast_pdf.status_code,
            "pdf_bytes": len(sast_pdf.content) if sast_pdf.status_code == 200 else 0,
        },
    )
    print(
        "DAST",
        {
            "task_id": dast_id,
            "status": dast_final["task"]["status"],
            "issue_count": (dast_final.get("result") or {}).get("issue_count"),
            "report_bytes": len(dast_report.content),
            "html_bytes": len(dast_html.content),
            "pdf_status": dast_pdf.status_code,
            "pdf_bytes": len(dast_pdf.content) if dast_pdf.status_code == 200 else 0,
            "target": DAST_TARGET,
        },
    )
    print(
        "AUDIT",
        {
            "items": len(audit_logs["data"]["items"]),
            "viewer": audit_logs["data"]["viewer"]["username"],
        },
    )

    if sast_final["task"]["status"] != "SUCCESS":
        raise RuntimeError(f"SAST final status is {sast_final['task']['status']}")
    if dast_final["task"]["status"] != "SUCCESS":
        raise RuntimeError(f"DAST final status is {dast_final['task']['status']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"INTEGRATION_CHECK_FAILED: {exc}")
        sys.exit(1)

