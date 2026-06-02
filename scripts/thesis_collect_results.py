#!/usr/bin/env python3
"""Collect thesis chapter 6 test data from the running demo system.

This script intentionally treats the Flask app as a black-box HTTP service for
security and performance cases. It only uses direct database access to prepare
stable test users/tasks so rate limits and duplicate registrations do not hide
the behavior being measured.
"""

from __future__ import annotations

import csv
import io
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
from flask_jwt_extended import create_access_token


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FIGURES = ROOT / "figures"
RAW_LOGS = FIGURES / "raw_logs"
BASE_URL = os.getenv("THESIS_BASE_URL", "http://127.0.0.1:5000/api")
DAST_TARGET = os.getenv("THESIS_DAST_TARGET", "http://127.0.0.1:3000")
PASSWORD = "StrongPass123"

sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import TaskStatus, TaskType, User, UserRole  # noqa: E402
from app.services.auth_service import ensure_admin_user  # noqa: E402
from app.services.task_service import create_task  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


@dataclass
class Prepared:
    admin_token: str
    user_a_token: str
    user_b_token: str
    user_a_id: int
    user_b_id: int
    user_b_task_id: int
    sample_sast_task_id: int | None


def ensure_dirs() -> None:
    FIGURES.mkdir(exist_ok=True)
    RAW_LOGS.mkdir(exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def log_json(name: str, payload: Any) -> None:
    (RAW_LOGS / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(method: str, path: str, *, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    started = time.perf_counter()
    response = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=90, **kwargs)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return response, elapsed_ms


def extract_message(response: requests.Response) -> str:
    try:
        payload = response.json()
        return str(payload.get("message") or payload.get("errors") or payload)[:240]
    except Exception:
        return response.text[:240]


def upsert_user(username: str, email: str, *, role: UserRole = UserRole.USER) -> User:
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, email=email, password_hash=hash_password(PASSWORD), role=role, is_active=True)
        db.session.add(user)
    else:
        user.email = email
        user.password_hash = hash_password(PASSWORD)
        user.role = role
        user.is_active = True
    db.session.commit()
    return user


def prepare_data() -> Prepared:
    app = create_app()
    with app.app_context():
        db.create_all()
        admin = ensure_admin_user("admin", "admin@example.com", "adminpass123")
        user_a = upsert_user("thesis_user_a", "thesis_user_a@example.com")
        user_b = upsert_user("thesis_user_b", "thesis_user_b@example.com")

        report_path = RAW_LOGS / "prepared_user_b_sast_report.json"
        report_path.write_text(json.dumps({"source": "prepared access-control report", "issues": []}), encoding="utf-8")
        user_b_task = create_task(
            user_id=user_b.id,
            task_type=TaskType.SAST,
            task_name=f"prepared-b-owned-{int(time.time())}",
            target_path=str(ROOT / "tests" / "sql_and_injection_demo.py"),
            scanner_engine="bandit",
        )
        user_b_task.status = TaskStatus.SUCCESS
        user_b_task.progress = 100
        user_b_task.report_path = str(report_path)
        user_b_task.result_summary = "prepared report for access-control check"
        db.session.commit()

        sample_sast_task_id = None
        sample = ROOT / "tests" / "sql_and_injection_demo.py"
        try:
            with sample.open("rb") as fh:
                response, _ = request_json(
                    "POST",
                    "/sast/tasks",
                    token=create_access_token(identity=str(user_a.id)),
                    data={"task_name": "latency-sast-seed", "scanner_engine": "bandit"},
                    files={"file": (sample.name, fh, "text/x-python")},
                )
            if response.status_code == 201:
                sample_sast_task_id = int(response.json()["data"]["task"]["id"])
        except Exception:
            sample_sast_task_id = None

        return Prepared(
            admin_token=create_access_token(identity=str(admin.id)),
            user_a_token=create_access_token(identity=str(user_a.id)),
            user_b_token=create_access_token(identity=str(user_b.id)),
            user_a_id=user_a.id,
            user_b_id=user_b.id,
            user_b_task_id=user_b_task.id,
            sample_sast_task_id=sample_sast_task_id,
        )


def build_functional_rows() -> list[dict[str, Any]]:
    result_path = RAW_LOGS / "functional_results.json"
    rows = json.loads(result_path.read_text(encoding="utf-8-sig")) if result_path.exists() else []
    mapping = {
        "smoke_test.py": ["Auth", "Task Management", "DAST"],
        "smoke_test_extra.py": ["SAST", "Report Export", "Task Management"],
        "smoke_test_sast.py": ["SAST"],
        "smoke_test_async.py": ["DAST", "Task Management"],
        "smoke_test_async_sast.py": ["SAST", "Task Management"],
        "smoke_test_cancel.py": ["Task Management"],
        "smoke_test_audit.py": ["Audit Logs"],
        "verify_all.py": ["Auth", "Task Management", "SAST", "DAST", "Report Export"],
        "verify_dast_real.py": ["DAST"],
        "verify_enhanced_results.py": ["SAST", "DAST"],
        "real_integration_check.py": ["Auth", "SAST", "DAST", "Report Export", "Audit Logs"],
    }
    modules = ["Auth", "Task Management", "SAST", "DAST", "SCA", "Report Export", "Audit Logs", "Admin Dashboard", "AI Analysis"]
    buckets = {module: {"module": module, "cases": 0, "passed": 0, "failed": 0, "failure_summary": ""} for module in modules}

    for item in rows:
        script = item["script"]
        mods = mapping.get(script, ["Task Management"])
        passed = int(item["exit_code"]) == 0
        err_text = Path(item["err"]).read_text(encoding="utf-8", errors="replace") if Path(item["err"]).exists() else ""
        out_text = Path(item["out"]).read_text(encoding="utf-8", errors="replace") if Path(item["out"]).exists() else ""
        reason = ""
        if not passed:
            combined = (err_text + "\n" + out_text).strip().splitlines()
            reason = next((line.strip() for line in reversed(combined) if line.strip()), f"{script} failed")
            reason = f"{script}: {reason[:120]}"
        for module in mods:
            bucket = buckets[module]
            bucket["cases"] += 1
            bucket["passed"] += 1 if passed else 0
            bucket["failed"] += 0 if passed else 1
            if reason:
                bucket["failure_summary"] = (bucket["failure_summary"] + "; " + reason).strip("; ")

    return list(buckets.values())


def run_security_cases(prepared: Prepared) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(category, case_name, payload_summary, response, expected_statuses, expected_text):
        passed = response.status_code in expected_statuses
        rows.append(
            {
                "category": category,
                "case_name": case_name,
                "payload_summary": payload_summary,
                "http_status": response.status_code,
                "expected": f"{sorted(expected_statuses)} {expected_text}",
                "actual": extract_message(response),
                "passed": "yes" if passed else "no",
            }
        )
        return response

    # Access control
    response, _ = request_json("GET", f"/sast/tasks/{prepared.user_b_task_id}", token=prepared.user_a_token)
    add("Access Control", "User A reads User B task", f"task_id={prepared.user_b_task_id}", response, {403, 404}, "blocked")
    response, _ = request_json("GET", f"/sast/tasks/{prepared.user_b_task_id}/report", token=prepared.user_a_token)
    add("Access Control", "User A downloads User B report", f"task_id={prepared.user_b_task_id}", response, {403, 404}, "blocked")
    response, _ = request_json("GET", "/admin/dashboard", token=prepared.user_a_token)
    add("Access Control", "Normal user opens admin dashboard", "/api/admin/dashboard", response, {403}, "forbidden")

    # Injection-like payloads
    response, _ = request_json("POST", "/auth/login", json={"username": "' OR '1'='1", "password": "' OR '1'='1"})
    add("Injection", "Login SQL payload", "' OR '1'='1", response, {400, 401, 429}, "not authenticated")
    response, _ = request_json("GET", "/tasks?page=1&page_size=20&task_type=' OR '1'='1", token=prepared.user_a_token)
    add("Injection", "Task type SQL payload", "task_type=' OR '1'='1", response, {400}, "invalid value")
    response, _ = request_json("GET", "/audit-logs?page=1&keyword=<script>alert(1)</script>", token=prepared.admin_token)
    add("Injection", "Audit keyword XSS payload", "<script>alert(1)</script>", response, {200}, "handled as data")

    # Upload validation
    large = io.BytesIO(b"0" * (21 * 1024 * 1024))
    response, _ = request_json(
        "POST",
        "/sast/tasks",
        token=prepared.user_a_token,
        data={"task_name": "oversize-upload"},
        files={"file": ("oversize.py", large, "text/x-python")},
    )
    add("File Upload", "Oversized file", "21MB .py", response, {400, 413}, "rejected")
    response, _ = request_json(
        "POST",
        "/sast/tasks",
        token=prepared.user_a_token,
        data={"task_name": "exe-upload"},
        files={"file": ("payload.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    add("File Upload", "Executable extension", ".exe", response, {400}, "unsupported type")
    response, _ = request_json(
        "POST",
        "/sast/tasks",
        token=prepared.user_a_token,
        data={"task_name": "zip-slip-name"},
        files={"file": ("../../etc/passwd", io.BytesIO(b"root:x:0:0"), "application/octet-stream")},
    )
    add("File Upload", "Path traversal filename", "../../etc/passwd", response, {400}, "rejected or neutralized")
    response, _ = request_json(
        "POST",
        "/sast/tasks",
        token=prepared.user_a_token,
        data={"task_name": "empty-file"},
        files={"file": ("empty.py", io.BytesIO(b""), "text/x-python")},
    )
    add("File Upload", "Empty file", "0 byte .py", response, {400, 422}, "rejected")

    # Token failures
    app = create_app()
    with app.app_context():
        expired = create_access_token(identity=str(prepared.user_a_id), expires_delta=timedelta(seconds=-1))
    response, _ = request_json("GET", "/auth/me", token=expired)
    add("Token Invalid", "Expired token", "expires_delta=-1s", response, {401}, "token expired")
    fake = prepared.user_a_token.rsplit(".", 1)[0] + ".invalidsignature"
    response, _ = request_json("GET", "/auth/me", token=fake)
    add("Token Invalid", "Forged signature token", "modified signature", response, {401, 422}, "token rejected")
    response, _ = request_json("GET", "/auth/me")
    add("Token Invalid", "Missing Authorization", "no header", response, {401}, "missing token")
    response, _ = request_json("GET", "/auth/me", headers={"Authorization": "Token abc"})
    add("Token Invalid", "Wrong auth scheme", "Token abc", response, {401, 422}, "malformed header")

    log_json("security_case_responses.json", rows)
    return rows


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def wait_for_task(path: str, token: str, timeout_seconds: int = 240) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last: dict[str, Any] = {}
    while time.time() < deadline:
        response, _ = request_json("GET", path, token=token)
        if response.status_code >= 400:
            raise RuntimeError(f"poll failed {path}: {response.status_code} {response.text[:300]}")
        last = response.json()["data"]
        status = last["task"]["status"]
        if status in {"SUCCESS", "FAILED", "TIMEOUT", "CANCELLED"}:
            return last
        time.sleep(2)
    raise TimeoutError(f"task did not finish: {path} last={last}")


def ensure_seed_sast_task(prepared: Prepared) -> int:
    if prepared.sample_sast_task_id:
        try:
            wait_for_task(f"/sast/tasks/{prepared.sample_sast_task_id}", prepared.user_a_token, timeout_seconds=120)
        except Exception:
            pass
        return prepared.sample_sast_task_id
    return prepared.user_b_task_id


def measure_api_latency(prepared: Prepared) -> list[dict[str, Any]]:
    task_id = ensure_seed_sast_task(prepared)
    endpoints = [
        ("POST /api/auth/login", "POST", "/auth/login", None, {"json": {"username": "admin", "password": "adminpass123"}}),
        ("GET /api/tasks?page=1&page_size=20", "GET", "/tasks?page=1&page_size=20", prepared.user_a_token, {}),
        ("GET /api/sast/tasks/{id}", "GET", f"/sast/tasks/{task_id}", prepared.user_a_token, {}),
        ("GET /api/admin/dashboard", "GET", "/admin/dashboard", prepared.admin_token, {}),
        ("GET /api/audit-logs?page=1", "GET", "/audit-logs?page=1", prepared.admin_token, {}),
        ("GET /api/sast/tasks/{id}/export?format=pdf", "GET", f"/sast/tasks/{task_id}/export?format=pdf", prepared.user_a_token, {}),
    ]
    rows = []
    details = []
    for label, method, path, token, kwargs in endpoints:
        samples = []
        statuses = []
        attempts = 0
        while len(samples) < 50 and attempts < 90:
            attempts += 1
            response, elapsed = request_json(method, path, token=token, **kwargs)
            statuses.append(response.status_code)
            details.append({"endpoint": label, "attempt": attempts, "status": response.status_code, "elapsed_ms": elapsed})
            if response.status_code == 429:
                time.sleep(6.2)
                continue
            samples.append(elapsed)
            if label.startswith("POST /api/auth/login"):
                time.sleep(6.2)
        rows.append(
            {
                "endpoint": label,
                "n": len(samples),
                "min": round(min(samples), 2) if samples else 0,
                "p50": round(percentile(samples, 0.50), 2),
                "p95": round(percentile(samples, 0.95), 2),
                "max": round(max(samples), 2) if samples else 0,
                "mean": round(statistics.mean(samples), 2) if samples else 0,
            }
        )
    log_json("perf_api_raw.json", details)
    return rows


def create_sca_zip() -> Path:
    zip_path = RAW_LOGS / "sca_demo.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        src = ROOT / "tests" / "sca_demo" / "requirements-vulnerable.txt"
        archive.write(src, "requirements.txt")
    return zip_path


def create_scan(kind: str, target: Path | str, token: str, run_idx: int) -> tuple[requests.Response, float]:
    started = time.perf_counter()
    if kind == "SAST":
        path = Path(target)
        with path.open("rb") as fh:
            response, _ = request_json(
                "POST",
                "/sast/tasks",
                token=token,
                data={"task_name": f"perf-sast-{run_idx}", "scanner_engine": "bandit"},
                files={"file": (path.name, fh, "text/x-python")},
            )
    elif kind == "SCA":
        path = Path(target)
        with path.open("rb") as fh:
            response, _ = request_json(
                "POST",
                "/sca/tasks",
                token=token,
                data={"task_name": f"perf-sca-{run_idx}"},
                files={"file": (path.name, fh, "application/zip")},
            )
    else:
        response, _ = request_json(
            "POST",
            "/dast/tasks",
            token=token,
            json={"task_name": f"perf-dast-{run_idx}", "target_url": str(target), "timeout": 30, "authorization_confirmed": True},
        )
    if response.status_code != 201:
        return response, (time.perf_counter() - started) * 1000
    task_id = response.json()["data"]["task"]["id"]
    wait_path = f"/{kind.lower()}/tasks/{task_id}"
    try:
        wait_for_task(wait_path, token, timeout_seconds=260 if kind != "DAST" else 120)
    except Exception:
        pass
    return response, (time.perf_counter() - started) * 1000


def measure_scan_duration(prepared: Prepared) -> list[dict[str, Any]]:
    sca_zip = create_sca_zip()
    cases = [
        ("SAST", ROOT / "tests" / "sql_and_injection_demo.py", 5),
        ("SCA", sca_zip, 5),
        ("DAST", DAST_TARGET, 3),
    ]
    rows = []
    for kind, target, count in cases:
        for run_idx in range(1, count + 1):
            response, duration = create_scan(kind, target, prepared.user_a_token, run_idx)
            rows.append(
                {
                    "task_type": kind,
                    "target": str(target),
                    "run_idx": run_idx,
                    "duration_ms": round(duration, 2),
                    "http_status": response.status_code,
                    "result": extract_message(response),
                }
            )
            time.sleep(1)
    return rows


def concurrency_one(token: str, idx: int) -> dict[str, Any]:
    path = ROOT / "tests" / "sql_and_injection_demo.py"
    started = time.perf_counter()
    try:
        with path.open("rb") as fh:
            response, _ = request_json(
                "POST",
                "/sast/tasks",
                token=token,
                data={"task_name": f"concurrency-sast-{int(time.time())}-{idx}", "scanner_engine": "bandit"},
                files={"file": (path.name, fh, "text/x-python")},
            )
        elapsed = (time.perf_counter() - started) * 1000
        return {"created": response.status_code == 201, "response_ms": elapsed, "status": response.status_code, "error": extract_message(response)}
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return {"created": False, "response_ms": elapsed, "status": 0, "error": str(exc)}


def measure_concurrency(prepared: Prepared) -> list[dict[str, Any]]:
    rows = []
    raw = []
    for count in [1, 5, 10, 20]:
        with ThreadPoolExecutor(max_workers=count) as pool:
            futures = [pool.submit(concurrency_one, prepared.user_b_token, idx) for idx in range(1, count + 1)]
            results = [future.result() for future in as_completed(futures)]
        created = [item for item in results if item["created"]]
        response_times = [item["response_ms"] for item in results]
        rows.append(
            {
                "parallel": count,
                "submitted": count,
                "created": len(created),
                "success_rate_percent": round(len(created) * 100 / count, 2),
                "avg_response_ms": round(statistics.mean(response_times), 2) if response_times else 0,
                "min_response_ms": round(min(response_times), 2) if response_times else 0,
                "max_response_ms": round(max(response_times), 2) if response_times else 0,
                "status_counts": json.dumps(dict(Counter(str(item["status"]) for item in results)), ensure_ascii=False),
            }
        )
        raw.append({"parallel": count, "results": results})
        time.sleep(62)
    log_json("perf_concurrency_raw.json", raw)
    return rows


def measure_compat_assets() -> list[dict[str, Any]]:
    dist = ROOT / "frontend" / "dist"
    if not dist.exists():
        return [
            {
                "asset": "frontend/dist",
                "path": str(dist),
                "bytes": 0,
                "download_ms": 0,
                "measured": "no",
                "note": "frontend/dist not found; browser GUI timing requires manual local measurement",
            }
        ]
    rows = []
    for path in [dist / "index.html", *sorted((dist / "assets").glob("*.js"))[:1], *sorted((dist / "assets").glob("*.css"))[:1]]:
        if not path.exists():
            continue
        started = time.perf_counter()
        data = path.read_bytes()
        elapsed = (time.perf_counter() - started) * 1000
        rows.append({"asset": path.name, "path": str(path), "bytes": len(data), "download_ms": round(elapsed, 2), "measured": "filesystem", "note": ""})
    return rows


def chart_functional(rows: list[dict[str, Any]]) -> None:
    labels = [row["module"] for row in rows]
    passed = [int(row["passed"]) for row in rows]
    failed = [int(row["failed"]) for row in rows]
    x = range(len(labels))
    plt.figure(figsize=(8, 4), dpi=150)
    plt.bar(x, passed, color="#2e7d32", label="Passed")
    plt.bar(x, failed, bottom=passed, color="#c62828", label="Failed")
    plt.xticks(list(x), labels, rotation=35, ha="right")
    plt.ylabel("Cases")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_2_functional.png")
    plt.close()


def chart_security(rows: list[dict[str, Any]]) -> None:
    categories = ["Access Control", "Injection", "File Upload", "Token Invalid"]
    good = []
    bad = []
    for category in categories:
        items = [row for row in rows if row["category"] == category]
        good.append(sum(1 for row in items if row["passed"] == "yes"))
        bad.append(sum(1 for row in items if row["passed"] != "yes"))
    x = range(len(categories))
    plt.figure(figsize=(8, 4), dpi=150)
    plt.bar(x, good, color="#2e7d32", label="Blocked/Handled")
    plt.bar(x, bad, bottom=good, color="#c62828", label="Not blocked")
    plt.xticks(list(x), categories, rotation=20, ha="right")
    plt.ylabel("Cases")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_3_security.png")
    plt.close()


def chart_api(rows: list[dict[str, Any]]) -> None:
    labels = [row["endpoint"].replace("/api/", "/") for row in rows]
    x = list(range(len(labels)))
    width = 0.38
    plt.figure(figsize=(8, 4), dpi=150)
    plt.bar([v - width / 2 for v in x], [float(row["p50"]) for row in rows], width=width, color="#1565c0", label="P50")
    plt.bar([v + width / 2 for v in x], [float(row["p95"]) for row in rows], width=width, color="#ef6c00", label="P95")
    plt.xticks(x, labels, rotation=35, ha="right")
    plt.ylabel("Latency (ms)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4a_api_latency.png")
    plt.close()


def chart_scan(rows: list[dict[str, Any]]) -> None:
    groups = ["SAST", "SCA", "DAST"]
    data = [[float(row["duration_ms"]) for row in rows if row["task_type"] == group] for group in groups]
    plt.figure(figsize=(8, 4), dpi=150)
    plt.boxplot(data, labels=groups, patch_artist=True, boxprops={"facecolor": "#bbdefb"})
    plt.ylabel("Duration (ms)")
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4b_scan_duration.png")
    plt.close()


def chart_concurrency(rows: list[dict[str, Any]]) -> None:
    x = [int(row["parallel"]) for row in rows]
    success = [float(row["success_rate_percent"]) for row in rows]
    avg = [float(row["avg_response_ms"]) for row in rows]
    fig, ax1 = plt.subplots(figsize=(8, 4), dpi=150)
    ax1.plot(x, success, marker="o", color="#2e7d32", label="Success rate")
    ax1.set_xlabel("Parallel submissions")
    ax1.set_ylabel("Success rate (%)", color="#2e7d32")
    ax1.set_ylim(0, 105)
    ax2 = ax1.twinx()
    ax2.plot(x, avg, marker="s", color="#1565c0", label="Avg response")
    ax2.set_ylabel("Avg response (ms)", color="#1565c0")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_6_4c_concurrency.png")
    plt.close(fig)


def chart_compat(rows: list[dict[str, Any]]) -> None:
    measured = [row for row in rows if row.get("measured") != "no"]
    if not measured:
        return
    labels = [row["asset"] for row in measured]
    sizes = [int(row["bytes"]) / 1024 for row in measured]
    plt.figure(figsize=(8, 4), dpi=150)
    plt.bar(range(len(labels)), sizes, color="#546e7a")
    plt.xticks(range(len(labels)), labels, rotation=25, ha="right")
    plt.ylabel("Size (KB)")
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4d_compat_assets.png")
    plt.close()


def env_info() -> dict[str, Any]:
    docker_version = "not available"
    try:
        docker_version = subprocess.check_output(
            [r"C:\Program Files\Docker\Docker\resources\bin\docker.exe", "--version"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception:
        pass
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": platform.processor() or platform.machine(),
        "docker": docker_version,
        "api_processes": len([p for p in subprocess.check_output("tasklist", text=True).splitlines() if "python.exe" in p.lower()]),
    }


def write_summary(functional, security, api_rows, scan_rows, concurrency_rows, compat_rows) -> None:
    total_func = sum(int(row["cases"]) for row in functional)
    pass_func = sum(int(row["passed"]) for row in functional)
    total_sec = len(security)
    pass_sec = sum(1 for row in security if row["passed"] == "yes")
    max_p95 = max(float(row["p95"]) for row in api_rows) if api_rows else 0
    max_parallel = max(concurrency_rows, key=lambda row: int(row["parallel"])) if concurrency_rows else {}
    lines = [
        "# Thesis Test Summary",
        "",
        "## 6.2 Functional Test Results",
        "",
        "| Module | Cases | Passed | Failed | Failure summary |",
        "|---|---:|---:|---:|---|",
    ]
    for row in functional:
        lines.append(f"| {row['module']} | {row['cases']} | {row['passed']} | {row['failed']} | {row['failure_summary'] or '-'} |")
    lines += [
        "",
        f"Functional scripts covered {total_func} module-level cases; {pass_func} passed and {total_func - pass_func} failed in this run.",
        "Figure: `fig_6_2_functional.png`.",
        "",
        "## 6.3 Security Test Results",
        "",
        "| Category | Case | Payload | HTTP status | Expected | Actual | Passed |",
        "|---|---|---|---:|---|---|---|",
    ]
    for row in security:
        lines.append(f"| {row['category']} | {row['case_name']} | `{row['payload_summary']}` | {row['http_status']} | {row['expected']} | {row['actual']} | {row['passed']} |")
    lines += [
        "",
        f"Security checks handled or blocked {pass_sec} of {total_sec} cases. Non-passing cases are retained as observed results, not rewritten.",
        "Figure: `fig_6_3_security.png`.",
        "",
        "## 6.4 Performance Test Results",
        "",
        "### API Latency",
        "",
        "| Endpoint | N | Min ms | P50 ms | P95 ms | Max ms | Mean ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in api_rows:
        lines.append(f"| {row['endpoint']} | {row['n']} | {row['min']} | {row['p50']} | {row['p95']} | {row['max']} | {row['mean']} |")
    lines += [
        "",
        f"Across measured API endpoints, the largest observed P95 latency was {max_p95:.2f} ms.",
        "Figure: `fig_6_4a_api_latency.png`.",
        "",
        "### Scan Duration",
        "",
        "| Type | Runs | Mean duration ms | Median duration ms |",
        "|---|---:|---:|---:|",
    ]
    for group in ["SAST", "SCA", "DAST"]:
        values = [float(row["duration_ms"]) for row in scan_rows if row["task_type"] == group]
        lines.append(f"| {group} | {len(values)} | {statistics.mean(values):.2f} | {statistics.median(values):.2f} |" if values else f"| {group} | 0 | 0 | 0 |")
    lines += [
        "",
        "Figure: `fig_6_4b_scan_duration.png`.",
        "",
        "### Concurrency",
        "",
        "| Parallel | Submitted | Created | Success rate % | Avg response ms | Status counts |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for row in concurrency_rows:
        lines.append(f"| {row['parallel']} | {row['submitted']} | {row['created']} | {row['success_rate_percent']} | {row['avg_response_ms']} | `{row['status_counts']}` |")
    if max_parallel:
        lines.append("")
        lines.append(f"At {max_parallel['parallel']} concurrent submissions, task creation success rate was {max_parallel['success_rate_percent']}% with average response {max_parallel['avg_response_ms']} ms.")
    lines += [
        "Figure: `fig_6_4c_concurrency.png`.",
        "",
        "## Compatibility Asset Loading",
        "",
        "| Asset | Bytes | Read/download ms | Measured | Note |",
        "|---|---:|---:|---|---|",
    ]
    for row in compat_rows:
        lines.append(f"| {row['asset']} | {row['bytes']} | {row['download_ms']} | {row['measured']} | {row['note']} |")
    lines += [
        "",
        "| Browser | Version | DOMContentLoaded ms | Evidence |",
        "|---|---|---:|---|",
        "| Chrome | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |",
        "| Edge | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |",
        "| Firefox | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |",
        "",
        "Browser version and GUI DOMContentLoaded values were not fabricated; they require manual measurement in the user's local browsers.",
        "Figure: `fig_6_4d_compat_assets.png` if generated.",
        "",
        "## Test Environment",
        "",
        "| Item | Value |",
        "|---|---|",
    ]
    for key, value in env_info().items():
        lines.append(f"| {key} | {value} |")
    lines += [
        f"| base_url | {BASE_URL} |",
        f"| dast_target | {DAST_TARGET} |",
        "",
        "## Issues Found During Testing",
        "",
        "- Several legacy smoke scripts fail under current validation/rate-limit behavior: missing `authorization_confirmed`, registration rate limit, or unhandled setup failure.",
        "- The implementation exposes dashboard data at `/api/admin/dashboard` and task summary at `/api/metrics/task-summary`; the requested `/api/metrics/dashboard` route was not present.",
        "- The generic `/api/tasks/{id}/report?format=pdf` route was not present; report export was measured through `/api/sast/tasks/{id}/export?format=pdf`.",
    ]
    (FIGURES / "THESIS_TEST_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    os.chdir(ROOT)
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    ensure_dirs()
    prepared = prepare_data()

    functional = build_functional_rows()
    write_csv(FIGURES / "test_functional.csv", functional, ["module", "cases", "passed", "failed", "failure_summary"])
    chart_functional(functional)

    security = run_security_cases(prepared)
    write_csv(FIGURES / "test_security.csv", security, ["category", "case_name", "payload_summary", "http_status", "expected", "actual", "passed"])
    chart_security(security)

    api_rows = measure_api_latency(prepared)
    write_csv(FIGURES / "test_perf_api.csv", api_rows, ["endpoint", "n", "min", "p50", "p95", "max", "mean"])
    chart_api(api_rows)

    scan_rows = measure_scan_duration(prepared)
    write_csv(FIGURES / "test_perf_scan.csv", scan_rows, ["task_type", "target", "run_idx", "duration_ms", "http_status", "result"])
    chart_scan(scan_rows)

    concurrency_rows = measure_concurrency(prepared)
    write_csv(
        FIGURES / "test_perf_concurrency.csv",
        concurrency_rows,
        ["parallel", "submitted", "created", "success_rate_percent", "avg_response_ms", "min_response_ms", "max_response_ms", "status_counts"],
    )
    chart_concurrency(concurrency_rows)

    compat_rows = measure_compat_assets()
    write_csv(FIGURES / "test_compat_assets.csv", compat_rows, ["asset", "path", "bytes", "download_ms", "measured", "note"])
    chart_compat(compat_rows)

    write_summary(functional, security, api_rows, scan_rows, concurrency_rows, compat_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
