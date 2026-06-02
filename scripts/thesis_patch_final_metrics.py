#!/usr/bin/env python3
"""Patch final thesis metrics with readable failures and quick concurrency data."""

from __future__ import annotations

import csv
import io
import json
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
from flask_jwt_extended import create_access_token

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FIGURES = ROOT / "figures"
BASE_URL = "http://127.0.0.1:5000/api"

sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


def write_csv(path: Path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def patch_functional():
    rows = read_csv(FIGURES / "test_functional.csv")
    reasons = {
        "Auth": "verify_all.py and real_integration_check.py hit registration rate limit (429 wrapped as 500)",
        "Task Management": "smoke_test_async.py missing authorization_confirmed; cancel/verify scripts hit setup login failure",
        "SAST": "verify_all.py and real_integration_check.py blocked by registration rate limit before SAST stage",
        "DAST": "smoke_test_async.py missing authorization_confirmed; integration scripts blocked before DAST completion",
        "Report Export": "verify_all.py and real_integration_check.py blocked before report export assertions",
        "Audit Logs": "smoke_test_audit.py setup user lookup failed; integration audit check blocked by rate limit",
    }
    for row in rows:
        if int(row["failed"]):
            row["failure_summary"] = reasons.get(row["module"], row["failure_summary"]).replace("|", "/")
        else:
            row["failure_summary"] = ""
    write_csv(FIGURES / "test_functional.csv", rows, ["module", "cases", "passed", "failed", "failure_summary"])


def token_for(username: str) -> str:
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, email=f"{username}@example.com", password_hash=hash_password("StrongPass123"), is_active=True)
            db.session.add(user)
        else:
            user.password_hash = hash_password("StrongPass123")
            user.is_active = True
        db.session.commit()
        return create_access_token(identity=str(user.id))


def create_one(token: str, idx: int):
    sample = ROOT / "tests" / "sql_and_injection_demo.py"
    start = time.perf_counter()
    try:
        with sample.open("rb") as fh:
            response = requests.post(
                f"{BASE_URL}/sast/tasks",
                headers={"Authorization": f"Bearer {token}"},
                data={"task_name": f"quick-concurrency-{int(time.time())}-{idx}", "scanner_engine": "bandit"},
                files={"file": (sample.name, fh, "text/x-python")},
                timeout=60,
            )
        elapsed = (time.perf_counter() - start) * 1000
        return {"created": response.status_code == 201, "response_ms": elapsed, "status": response.status_code}
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        return {"created": False, "response_ms": elapsed, "status": 0}


def run_concurrency():
    rows = []
    for parallel in [1, 5, 10, 20]:
        token = token_for(f"thesis_concurrency_{parallel}_{int(time.time())}")
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            results = [future.result() for future in as_completed([pool.submit(create_one, token, idx) for idx in range(1, parallel + 1)])]
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
        time.sleep(3)
    write_csv(FIGURES / "test_perf_concurrency.csv", rows, ["parallel", "submitted", "created", "success_rate_percent", "avg_response_ms", "min_response_ms", "max_response_ms", "status_counts"])
    return rows


def chart_functional():
    rows = read_csv(FIGURES / "test_functional.csv")
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


def chart_concurrency(rows):
    x = [int(row["parallel"]) for row in rows]
    success = [float(row["success_rate_percent"]) for row in rows]
    avg = [float(row["avg_response_ms"]) for row in rows]
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


def patch_summary():
    from thesis_finalize_from_observations import compat_rows, scan_rows, write_summary

    write_summary(scan_rows(), compat_rows())


def main():
    patch_functional()
    concurrency = run_concurrency()
    chart_functional()
    chart_concurrency(concurrency)
    patch_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
