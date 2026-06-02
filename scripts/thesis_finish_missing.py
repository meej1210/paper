#!/usr/bin/env python3
"""Finish missing thesis artifacts without re-running the slow full collector."""

from __future__ import annotations

import csv
import io
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
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
BASE_URL = "http://127.0.0.1:5000/api"
DAST_TARGET = "http://127.0.0.1:3000"
PASSWORD = "StrongPass123"

sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Task, TaskStatus, TaskType, User, UserRole  # noqa: E402
from app.services.dast_service import run_dast_scan  # noqa: E402
from app.services.sast_service import run_bandit_scan  # noqa: E402
from app.services.sca_service import run_pip_audit_scan  # noqa: E402
from app.services.task_service import create_task  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def ensure_user(app) -> tuple[User, str]:
    with app.app_context():
        user = User.query.filter_by(username="thesis_finish_user").first()
        if not user:
            user = User(username="thesis_finish_user", email="thesis_finish_user@example.com", password_hash=hash_password(PASSWORD), role=UserRole.USER)
            db.session.add(user)
        else:
            user.password_hash = hash_password(PASSWORD)
            user.is_active = True
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        return user, token


def make_sca_zip() -> Path:
    zip_path = RAW_LOGS / "finish_sca_demo.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT / "tests" / "sca_demo" / "requirements-vulnerable.txt", "requirements.txt")
    return zip_path


def run_scan_rows() -> list[dict[str, Any]]:
    app = create_app()
    rows: list[dict[str, Any]] = []
    sca_zip = make_sca_zip()
    with app.app_context():
        user, _ = ensure_user(app)
        cases = [
            ("SAST", ROOT / "tests" / "sql_and_injection_demo.py", 5, run_bandit_scan),
            ("SCA", sca_zip, 3, run_pip_audit_scan),
            ("DAST", DAST_TARGET, 3, run_dast_scan),
        ]
        for kind, target, count, runner in cases:
            for idx in range(1, count + 1):
                task = create_task(
                    user_id=user.id,
                    task_type=TaskType(kind),
                    task_name=f"finish-{kind.lower()}-{idx}-{int(time.time())}",
                    target_path=str(target) if kind in {"SAST", "SCA"} else None,
                    target_url=str(target) if kind == "DAST" else None,
                    timeout_seconds=30 if kind == "DAST" else None,
                    scanner_engine="bandit" if kind == "SAST" else None,
                    authorization_confirmed=kind == "DAST",
                    target_host="127.0.0.1" if kind == "DAST" else None,
                    target_ip="127.0.0.1" if kind == "DAST" else None,
                    target_policy="localhost" if kind == "DAST" else None,
                )
                start = time.perf_counter()
                runner(task)
                duration = (time.perf_counter() - start) * 1000
                db.session.refresh(task)
                rows.append(
                    {
                        "task_type": kind,
                        "target": str(target),
                        "run_idx": idx,
                        "duration_ms": round(duration, 2),
                        "http_status": "direct_service",
                        "result": task.status.value,
                    }
                )
    return rows


def request_create(token: str, idx: int) -> dict[str, Any]:
    path = ROOT / "tests" / "sql_and_injection_demo.py"
    headers = {"Authorization": f"Bearer {token}"}
    start = time.perf_counter()
    try:
        with path.open("rb") as fh:
            response = requests.post(
                f"{BASE_URL}/sast/tasks",
                headers=headers,
                data={"task_name": f"finish-concurrency-{int(time.time())}-{idx}", "scanner_engine": "bandit"},
                files={"file": (path.name, fh, "text/x-python")},
                timeout=60,
            )
        elapsed = (time.perf_counter() - start) * 1000
        try:
            message = response.json().get("message")
        except Exception:
            message = response.text[:200]
        return {"created": response.status_code == 201, "response_ms": elapsed, "status": response.status_code, "message": message}
    except Exception as exc:
        return {"created": False, "response_ms": (time.perf_counter() - start) * 1000, "status": 0, "message": str(exc)}


def run_concurrency_rows() -> list[dict[str, Any]]:
    app = create_app()
    _, token = ensure_user(app)
    rows: list[dict[str, Any]] = []
    raw: list[dict[str, Any]] = []
    for parallel in [1, 5, 10, 20]:
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            results = [future.result() for future in as_completed([pool.submit(request_create, token, idx) for idx in range(1, parallel + 1)])]
        times = [item["response_ms"] for item in results]
        created = sum(1 for item in results if item["created"])
        rows.append(
            {
                "parallel": parallel,
                "submitted": parallel,
                "created": created,
                "success_rate_percent": round(created * 100 / parallel, 2),
                "avg_response_ms": round(statistics.mean(times), 2),
                "min_response_ms": round(min(times), 2),
                "max_response_ms": round(max(times), 2),
                "status_counts": json.dumps(dict(Counter(str(item["status"]) for item in results)), ensure_ascii=False),
            }
        )
        raw.append({"parallel": parallel, "results": results})
        time.sleep(62)
    (RAW_LOGS / "finish_concurrency_raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def compat_rows() -> list[dict[str, Any]]:
    dist = ROOT / "frontend" / "dist"
    if not dist.exists():
        return [{"asset": "frontend/dist", "path": str(dist), "bytes": 0, "download_ms": 0, "measured": "no", "note": "frontend/dist not found"}]
    paths = [dist / "index.html"]
    assets = dist / "assets"
    if assets.exists():
        paths.extend(sorted(assets.glob("*.js"))[:1])
        paths.extend(sorted(assets.glob("*.css"))[:1])
    rows = []
    for path in paths:
        if not path.exists():
            continue
        start = time.perf_counter()
        size = len(path.read_bytes())
        rows.append({"asset": path.name, "path": str(path), "bytes": size, "download_ms": round((time.perf_counter() - start) * 1000, 2), "measured": "filesystem", "note": ""})
    return rows or [{"asset": "frontend/dist", "path": str(dist), "bytes": 0, "download_ms": 0, "measured": "no", "note": "no index/js/css assets found"}]


def charts(scan_rows, concurrency_rows, compat):
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    groups = ["SAST", "SCA", "DAST"]
    data = [[float(row["duration_ms"]) for row in scan_rows if row["task_type"] == group] for group in groups]
    plt.figure(figsize=(8, 4), dpi=150)
    plt.boxplot(data, labels=groups, patch_artist=True, boxprops={"facecolor": "#bbdefb"})
    plt.ylabel("Duration (ms)")
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4b_scan_duration.png")
    plt.close()

    x = [int(row["parallel"]) for row in concurrency_rows]
    success = [float(row["success_rate_percent"]) for row in concurrency_rows]
    avg = [float(row["avg_response_ms"]) for row in concurrency_rows]
    fig, ax1 = plt.subplots(figsize=(8, 4), dpi=150)
    ax1.plot(x, success, marker="o", color="#2e7d32")
    ax1.set_xlabel("Parallel submissions")
    ax1.set_ylabel("Success rate (%)", color="#2e7d32")
    ax1.set_ylim(0, 105)
    ax2 = ax1.twinx()
    ax2.plot(x, avg, marker="s", color="#1565c0")
    ax2.set_ylabel("Avg response (ms)", color="#1565c0")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_6_4c_concurrency.png")
    plt.close(fig)

    measured = [row for row in compat if row["measured"] != "no"]
    if measured:
        plt.figure(figsize=(8, 4), dpi=150)
        plt.bar(range(len(measured)), [int(row["bytes"]) / 1024 for row in measured], color="#546e7a")
        plt.xticks(range(len(measured)), [row["asset"] for row in measured], rotation=25, ha="right")
        plt.ylabel("Size (KB)")
        plt.tight_layout()
        plt.savefig(FIGURES / "fig_6_4d_compat_assets.png")
        plt.close()


def env_info() -> dict[str, Any]:
    docker = "not available"
    try:
        docker = subprocess.check_output([r"C:\Program Files\Docker\Docker\resources\bin\docker.exe", "--version"], text=True).strip()
    except Exception:
        pass
    return {
        "OS": platform.platform(),
        "Python": platform.python_version(),
        "CPU": platform.processor() or platform.machine(),
        "Docker": docker,
        "Base URL": BASE_URL,
        "DAST target": DAST_TARGET,
    }


def write_summary():
    functional = read_csv(FIGURES / "test_functional.csv")
    security = read_csv(FIGURES / "test_security.csv")
    api_rows = read_csv(FIGURES / "test_perf_api.csv")
    scan_rows = read_csv(FIGURES / "test_perf_scan.csv")
    concurrency = read_csv(FIGURES / "test_perf_concurrency.csv")
    compat = read_csv(FIGURES / "test_compat_assets.csv")

    total_func = sum(int(row["cases"]) for row in functional)
    passed_func = sum(int(row["passed"]) for row in functional)
    passed_sec = sum(1 for row in security if row["passed"] == "yes")
    max_p95 = max(float(row["p95"]) for row in api_rows)
    max_parallel = max(concurrency, key=lambda row: int(row["parallel"]))

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
    lines += ["", f"Functional scripts produced {total_func} module-level observations: {passed_func} passed and {total_func - passed_func} failed.", "Figure: `fig_6_2_functional.png`.", ""]

    lines += ["## 6.3 Security Test Results", "", "| Category | Case | Payload | HTTP status | Expected | Actual | Passed |", "|---|---|---|---:|---|---|---|"]
    for row in security:
        lines.append(f"| {row['category']} | {row['case_name']} | `{row['payload_summary']}` | {row['http_status']} | {row['expected']} | {row['actual']} | {row['passed']} |")
    lines += ["", f"Security checks blocked or safely handled {passed_sec} of {len(security)} cases.", "Figure: `fig_6_3_security.png`.", ""]

    lines += ["## 6.4 Performance Test Results", "", "### API Latency", "", "| Endpoint | N | Min ms | P50 ms | P95 ms | Max ms | Mean ms |", "|---|---:|---:|---:|---:|---:|---:|"]
    for row in api_rows:
        lines.append(f"| {row['endpoint']} | {row['n']} | {row['min']} | {row['p50']} | {row['p95']} | {row['max']} | {row['mean']} |")
    lines += ["", f"The highest measured API P95 latency was {max_p95:.2f} ms.", "Figure: `fig_6_4a_api_latency.png`.", ""]

    lines += ["### Scan Duration", "", "| Type | Runs | Mean duration ms | Median duration ms |", "|---|---:|---:|---:|"]
    for kind in ["SAST", "SCA", "DAST"]:
        vals = [float(row["duration_ms"]) for row in scan_rows if row["task_type"] == kind]
        lines.append(f"| {kind} | {len(vals)} | {statistics.mean(vals):.2f} | {statistics.median(vals):.2f} |")
    lines += ["", "Figure: `fig_6_4b_scan_duration.png`.", ""]

    lines += ["### Concurrency", "", "| Parallel | Submitted | Created | Success rate % | Avg response ms | Status counts |", "|---:|---:|---:|---:|---:|---|"]
    for row in concurrency:
        lines.append(f"| {row['parallel']} | {row['submitted']} | {row['created']} | {row['success_rate_percent']} | {row['avg_response_ms']} | `{row['status_counts']}` |")
    lines += ["", f"At {max_parallel['parallel']} concurrent submissions, creation success rate was {max_parallel['success_rate_percent']}% and average response time was {max_parallel['avg_response_ms']} ms.", "Figure: `fig_6_4c_concurrency.png`.", ""]

    lines += ["## Compatibility Asset Loading", "", "| Asset | Bytes | Read/download ms | Measured | Note |", "|---|---:|---:|---|---|"]
    for row in compat:
        lines.append(f"| {row['asset']} | {row['bytes']} | {row['download_ms']} | {row['measured']} | {row['note']} |")
    lines += [
        "",
        "| Browser | Version | DOMContentLoaded ms | Evidence |",
        "|---|---|---:|---|",
        "| Chrome | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |",
        "| Edge | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |",
        "| Firefox | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |",
        "",
        "Browser versions and GUI DOMContentLoaded values were not fabricated; they require manual measurement in local browsers.",
        "Figure: `fig_6_4d_compat_assets.png` if generated.",
        "",
        "## Test Environment",
        "",
        "| Item | Value |",
        "|---|---|",
    ]
    for k, v in env_info().items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "## Issues Found During Testing",
        "",
        "- Legacy smoke scripts failed under current validation/rate-limit behavior: missing `authorization_confirmed`, registration rate limit, or unhandled setup failure.",
        "- One file-upload case accepted an empty `.py` file with HTTP 201; this is recorded as a failed security expectation.",
        "- During the initial full collector, some async SCA tasks remained `PENDING` even though the Celery worker logged task completion; scan-duration values in `test_perf_scan.csv` therefore use direct service invocations and the async issue is recorded here.",
        "- Requested routes `/api/metrics/dashboard` and `/api/tasks/{id}/report?format=pdf` were not present; measured equivalents were `/api/admin/dashboard` and `/api/sast/tasks/{id}/export?format=pdf`.",
    ]
    (FIGURES / "THESIS_TEST_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    FIGURES.mkdir(exist_ok=True)
    RAW_LOGS.mkdir(exist_ok=True)
    scan = run_scan_rows()
    write_csv(FIGURES / "test_perf_scan.csv", scan, ["task_type", "target", "run_idx", "duration_ms", "http_status", "result"])
    conc = run_concurrency_rows()
    write_csv(FIGURES / "test_perf_concurrency.csv", conc, ["parallel", "submitted", "created", "success_rate_percent", "avg_response_ms", "min_response_ms", "max_response_ms", "status_counts"])
    comp = compat_rows()
    write_csv(FIGURES / "test_compat_assets.csv", comp, ["asset", "path", "bytes", "download_ms", "measured", "note"])
    charts(scan, conc, comp)
    write_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
