#!/usr/bin/env python3
"""Generate final thesis artifacts from observations already collected."""

from __future__ import annotations

import csv
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FIGURES = ROOT / "figures"
RAW_LOGS = FIGURES / "raw_logs"

sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.models import Task  # noqa: E402


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def scan_rows() -> list[dict[str, Any]]:
    app = create_app()
    rows: list[dict[str, Any]] = []
    with app.app_context():
        specs = [
            ("SAST", [100, 99, 98, 97, 96], ROOT / "tests" / "sql_and_injection_demo.py"),
            ("SCA", [103, 102, 101], ROOT / "tests" / "sca_demo"),
            ("DAST", [80, 78, 58], "http://127.0.0.1:3000"),
        ]
        for kind, ids, target in specs:
            for idx, task_id in enumerate(ids, 1):
                task = Task.query.get(task_id)
                if not task or task.duration_ms is None:
                    continue
                rows.append(
                    {
                        "task_type": kind,
                        "target": str(target),
                        "run_idx": idx,
                        "duration_ms": int(task.duration_ms),
                        "http_status": "db_observed",
                        "result": task.status.value,
                    }
                )
    return rows


def concurrency_rows() -> list[dict[str, Any]]:
    # Real HTTP concurrency collection was started but exceeded the session time
    # budget. Record the measured status honestly instead of fabricating values.
    return [
        {
            "parallel": level,
            "submitted": 0,
            "created": 0,
            "success_rate_percent": "",
            "avg_response_ms": "",
            "min_response_ms": "",
            "max_response_ms": "",
            "status_counts": "not measured: concurrency collection exceeded time budget after scan phase",
        }
        for level in [1, 5, 10, 20]
    ]


def compat_rows() -> list[dict[str, Any]]:
    dist = ROOT / "frontend" / "dist"
    if not dist.exists():
        return [{"asset": "frontend/dist", "path": str(dist), "bytes": 0, "download_ms": 0, "measured": "no", "note": "frontend/dist not found; run frontend build before asset timing"}]
    paths = [dist / "index.html"]
    assets = dist / "assets"
    if assets.exists():
        paths.extend(sorted(assets.glob("*.js"))[:1])
        paths.extend(sorted(assets.glob("*.css"))[:1])
    rows = []
    for path in paths:
        if path.exists():
            start = time.perf_counter()
            size = len(path.read_bytes())
            rows.append({"asset": path.name, "path": str(path), "bytes": size, "download_ms": round((time.perf_counter() - start) * 1000, 2), "measured": "filesystem", "note": ""})
    return rows or [{"asset": "frontend/dist", "path": str(dist), "bytes": 0, "download_ms": 0, "measured": "no", "note": "no index/js/css assets found"}]


def charts(scan: list[dict[str, Any]], compat: list[dict[str, Any]]) -> None:
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    groups = ["SAST", "SCA", "DAST"]
    data = [[float(row["duration_ms"]) for row in scan if row["task_type"] == group] for group in groups]
    plt.figure(figsize=(8, 4), dpi=150)
    plt.boxplot(data, labels=groups, patch_artist=True, boxprops={"facecolor": "#bbdefb"})
    plt.ylabel("Duration (ms)")
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4b_scan_duration.png")
    plt.close()

    plt.figure(figsize=(8, 4), dpi=150)
    plt.text(0.5, 0.55, "Concurrency collection not completed", ha="center", va="center", fontsize=16)
    plt.text(0.5, 0.42, "See test_perf_concurrency.csv and summary notes", ha="center", va="center", fontsize=10)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4c_concurrency.png")
    plt.close()

    measured = [row for row in compat if row["measured"] != "no"]
    if measured:
        plt.figure(figsize=(8, 4), dpi=150)
        plt.bar(range(len(measured)), [int(row["bytes"]) / 1024 for row in measured], color="#546e7a")
        plt.xticks(range(len(measured)), [row["asset"] for row in measured], rotation=25, ha="right")
        plt.ylabel("Size (KB)")
        plt.tight_layout()
        plt.savefig(FIGURES / "fig_6_4d_compat_assets.png")
        plt.close()
    else:
        plt.figure(figsize=(8, 4), dpi=150)
        plt.text(0.5, 0.5, "frontend/dist not found", ha="center", va="center", fontsize=16)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(FIGURES / "fig_6_4d_compat_assets.png")
        plt.close()


def env_info() -> dict[str, Any]:
    docker = "not available"
    compose = "not available"
    try:
        docker = subprocess.check_output([r"C:\Program Files\Docker\Docker\resources\bin\docker.exe", "--version"], text=True).strip()
        compose = subprocess.check_output([r"C:\Program Files\Docker\Docker\resources\bin\docker.exe", "compose", "ps"], text=True, stderr=subprocess.STDOUT).strip().replace("\n", "<br>")
    except Exception:
        pass
    return {
        "OS": platform.platform(),
        "Python": platform.python_version(),
        "CPU": platform.processor() or platform.machine(),
        "Docker": docker,
        "Docker services": compose,
        "Backend URL": "http://127.0.0.1:5000/api",
        "DAST target": "http://127.0.0.1:3000",
    }


def write_summary(scan: list[dict[str, Any]], compat: list[dict[str, Any]]) -> None:
    functional = read_csv(FIGURES / "test_functional.csv")
    security = read_csv(FIGURES / "test_security.csv")
    api = read_csv(FIGURES / "test_perf_api.csv")
    concurrency = read_csv(FIGURES / "test_perf_concurrency.csv")
    total_func = sum(int(row["cases"]) for row in functional)
    passed_func = sum(int(row["passed"]) for row in functional)
    passed_sec = sum(1 for row in security if row["passed"] == "yes")
    max_p95 = max(float(row["p95"]) for row in api)

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
    for row in api:
        lines.append(f"| {row['endpoint']} | {row['n']} | {row['min']} | {row['p50']} | {row['p95']} | {row['max']} | {row['mean']} |")
    lines += ["", f"The highest measured API P95 latency was {max_p95:.2f} ms.", "Figure: `fig_6_4a_api_latency.png`.", ""]

    lines += ["### Scan Duration", "", "| Type | Runs | Mean duration ms | Median duration ms | Notes |", "|---|---:|---:|---:|---|"]
    for kind in ["SAST", "SCA", "DAST"]:
        vals = [float(row["duration_ms"]) for row in scan if row["task_type"] == kind]
        notes = "database-observed task duration_ms from real scanner runs"
        lines.append(f"| {kind} | {len(vals)} | {statistics.mean(vals):.2f} | {statistics.median(vals):.2f} | {notes} |")
    lines += ["", "Figure: `fig_6_4b_scan_duration.png`.", ""]

    lines += ["### Concurrency", "", "| Parallel | Submitted | Created | Success rate % | Avg response ms | Status counts |", "|---:|---:|---:|---:|---:|---|"]
    for row in concurrency:
        lines.append(f"| {row['parallel']} | {row['submitted']} | {row['created']} | {row['success_rate_percent']} | {row['avg_response_ms']} | `{row['status_counts']}` |")
    lines += ["", "Concurrency creation metrics were not completed within the run budget after repeated slow SCA/DAST phases; values are intentionally left unfilled rather than fabricated.", "Figure: `fig_6_4c_concurrency.png`.", ""]

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
        "Figure: `fig_6_4d_compat_assets.png`.",
        "",
        "## Test Environment",
        "",
        "| Item | Value |",
        "|---|---|",
    ]
    for key, value in env_info().items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        "## Issues Found During Testing",
        "",
        "- Legacy smoke scripts failed under current validation/rate-limit behavior: missing `authorization_confirmed`, registration rate limit, or unhandled setup failure.",
        "- One file-upload case accepted an empty `.py` file with HTTP 201; this is recorded as a failed security expectation.",
        "- During collection, an async SCA task remained non-terminal for a long period and caused timeout; scan duration table uses database-observed real task durations instead of fabricated retry values.",
        "- Requested routes `/api/metrics/dashboard` and `/api/tasks/{id}/report?format=pdf` were not present; measured equivalents were `/api/admin/dashboard` and `/api/sast/tasks/{id}/export?format=pdf`.",
    ]
    (FIGURES / "THESIS_TEST_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    FIGURES.mkdir(exist_ok=True)
    RAW_LOGS.mkdir(exist_ok=True)
    scan = scan_rows()
    compat = compat_rows()
    concurrency = concurrency_rows()
    write_csv(FIGURES / "test_perf_scan.csv", scan, ["task_type", "target", "run_idx", "duration_ms", "http_status", "result"])
    write_csv(FIGURES / "test_perf_concurrency.csv", concurrency, ["parallel", "submitted", "created", "success_rate_percent", "avg_response_ms", "min_response_ms", "max_response_ms", "status_counts"])
    write_csv(FIGURES / "test_compat_assets.csv", compat, ["asset", "path", "bytes", "download_ms", "measured", "note"])
    charts(scan, compat)
    write_summary(scan, compat)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
