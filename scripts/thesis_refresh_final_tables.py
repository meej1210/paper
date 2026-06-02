#!/usr/bin/env python3
"""Refresh final thesis tables from real post-fix verification runs."""

from __future__ import annotations

import csv
import json
import platform
import re
import statistics
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FIGURES = ROOT / "figures"
RAW_LOGS = FIGURES / "raw_logs"
DAST_TARGET = "http://127.0.0.1:3000"

sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Task, TaskStatus, TaskType, User, UserRole  # noqa: E402
from app.services.dast_service import run_dast_scan  # noqa: E402
from app.services.sast_service import run_bandit_scan  # noqa: E402
from app.services.sca_service import run_pip_audit_scan  # noqa: E402
from app.services.task_service import create_task  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


MODULE_LABELS = {
    "Auth": "用户认证",
    "Task Management": "任务管理",
    "SAST": "静态扫描",
    "DAST": "动态扫描",
    "SCA": "依赖审计",
    "Report Export": "报告导出",
    "Audit Logs": "审计日志",
    "Admin Dashboard": "管理看板",
    "AI Analysis": "AI 分析",
}

SECURITY_LABELS = {
    "Access Control": "越权访问",
    "Injection": "注入攻击",
    "File Upload": "文件上传",
    "Token Invalid": "令牌失效",
}

ENDPOINT_LABELS = {
    "POST /api/auth/login": "登录",
    "GET /api/tasks?page=1&page_size=20": "任务列表",
    "GET /api/sast/tasks/{id}": "任务详情",
    "GET /api/admin/dashboard": "管理看板",
    "GET /api/audit-logs?page=1": "审计日志",
    "GET /api/sast/tasks/{id}/export?format=pdf": "PDF 导出",
}

SCAN_LABELS = {"SAST": "静态扫描", "SCA": "依赖审计", "DAST": "动态扫描"}


def configure_plot_style() -> None:
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans SC", "Microsoft JhengHei", "SimSun"]
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 10


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_pytest_log(name: str, args: list[str]) -> tuple[int, str]:
    output_path = RAW_LOGS / f"{name}.out.log"
    error_path = RAW_LOGS / f"{name}.err.log"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *args, "-q"],
        cwd=BACKEND,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    output_path.write_text(completed.stdout, encoding="utf-8")
    error_path.write_text(completed.stderr, encoding="utf-8")
    combined = f"{completed.stdout}\n{completed.stderr}"
    return completed.returncode, combined


def extract_passed(output: str) -> int:
    matches = re.findall(r"(\d+)\s+passed\b", output)
    return int(matches[-1]) if matches else 0


def refresh_functional() -> list[dict[str, Any]]:
    rows = read_csv(FIGURES / "test_functional.csv")
    supplemental = {
        "SCA": ("functional_afterfix_pytest_sca", ["tests/test_sca_api.py", "tests/test_sca_service.py"]),
        "Admin Dashboard": (
            "functional_afterfix_pytest_admin_metrics",
            ["tests/test_admin_dashboard.py", "tests/test_metrics.py"],
        ),
        "AI Analysis": ("functional_afterfix_pytest_ai", ["tests/test_ai_service.py"]),
    }
    evidence: dict[str, dict[str, Any]] = {}
    for module, (log_name, pytest_args) in supplemental.items():
        code, output = run_pytest_log(log_name, pytest_args)
        passed = extract_passed(output)
        evidence[module] = {
            "cases": passed if code == 0 else passed + 1,
            "passed": passed if code == 0 else passed,
            "failed": 0 if code == 0 else 1,
            "failure_summary": "" if code == 0 else f"{log_name} failed; see raw_logs/{log_name}.*.log",
        }

    for row in rows:
        module = row["module"]
        if module in evidence:
            row.update({key: str(value) for key, value in evidence[module].items()})

    write_csv(FIGURES / "test_functional.csv", rows, ["module", "cases", "passed", "failed", "failure_summary"])
    return rows


def ensure_user_id(app) -> int:
    with app.app_context():
        user = User.query.filter_by(username="thesis_final_refresh").first()
        if not user:
            user = User(
                username="thesis_final_refresh",
                email="thesis_final_refresh@example.com",
                password_hash=hash_password("StrongPass123"),
                role=UserRole.USER,
                is_active=True,
            )
            db.session.add(user)
        else:
            user.password_hash = hash_password("StrongPass123")
            user.is_active = True
        db.session.commit()
        return int(user.id)


def make_sca_zip() -> Path:
    zip_path = RAW_LOGS / "final_sca_demo.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT / "tests" / "sca_demo" / "requirements-vulnerable.txt", "requirements.txt")
    return zip_path


def refresh_scan_rows() -> list[dict[str, Any]]:
    app = create_app()
    rows: list[dict[str, Any]] = []
    sca_zip = make_sca_zip()
    with app.app_context():
        user_id = ensure_user_id(app)
        cases = [
            ("SAST", ROOT / "tests" / "sql_and_injection_demo.py", 5, run_bandit_scan),
            ("SCA", sca_zip, 3, run_pip_audit_scan),
            ("DAST", DAST_TARGET, 3, run_dast_scan),
        ]
        for kind, target, count, runner in cases:
            for idx in range(1, count + 1):
                task = create_task(
                    user_id=user_id,
                    task_type=TaskType(kind),
                    task_name=f"final-{kind.lower()}-{idx}-{int(time.time())}",
                    target_path=str(target) if kind in {"SAST", "SCA"} else None,
                    target_url=str(target) if kind == "DAST" else None,
                    timeout_seconds=30 if kind == "DAST" else None,
                    scanner_engine="bandit" if kind == "SAST" else None,
                    authorization_confirmed=kind == "DAST",
                    target_host="127.0.0.1" if kind == "DAST" else None,
                    target_ip="127.0.0.1" if kind == "DAST" else None,
                    target_policy="localhost" if kind == "DAST" else None,
                )
                started = time.perf_counter()
                runner(task)
                duration = (time.perf_counter() - started) * 1000
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
    write_csv(FIGURES / "test_perf_scan.csv", rows, ["task_type", "target", "run_idx", "duration_ms", "http_status", "result"])
    return rows


def chart_functional(rows: list[dict[str, Any]]) -> None:
    labels = [MODULE_LABELS.get(row["module"], row["module"]) for row in rows]
    passed = [int(row["passed"]) for row in rows]
    failed = [int(row["failed"]) for row in rows]
    x = range(len(labels))
    plt.figure(figsize=(8, 4.6), dpi=150)
    plt.bar(x, passed, color="#2e7d32", label="通过")
    plt.bar(x, failed, bottom=passed, color="#c62828", label="失败")
    plt.xticks(list(x), labels, rotation=35, ha="right")
    plt.ylabel("用例数")
    plt.title("功能测试通过情况")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_2_functional.png")
    plt.close()


def chart_scan(rows: list[dict[str, Any]]) -> None:
    groups = ["SAST", "SCA", "DAST"]
    data_ms = [[float(row["duration_ms"]) for row in rows if row["task_type"] == group] for group in groups]
    means = [statistics.mean(values) / 1000 for values in data_ms]
    y = list(range(len(groups)))

    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=150)
    bars = ax.barh(y, means, color=["#2e7d32", "#1565c0", "#ef6c00"], alpha=0.82, label="平均耗时")
    for index, values in enumerate(data_ms):
        seconds = [value / 1000 for value in values]
        ax.scatter(seconds, [index] * len(seconds), color="#263238", s=24, zorder=3, label="单次样本" if index == 0 else None)
    for bar, mean in zip(bars, means):
        ax.text(bar.get_width() + max(means) * 0.015, bar.get_y() + bar.get_height() / 2, f"{mean:.2f}s", va="center")
    ax.set_yticks(y, [SCAN_LABELS[group] for group in groups])
    ax.set_xlabel("耗时（秒）")
    ax.set_title("扫描任务耗时对比")
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4b_scan_duration.png")
    plt.close()


def chart_security(rows: list[dict[str, str]]) -> None:
    categories = ["Access Control", "Injection", "File Upload", "Token Invalid"]
    passed = []
    failed = []
    for category in categories:
        items = [row for row in rows if row["category"] == category]
        passed.append(sum(1 for row in items if row["passed"] == "yes"))
        failed.append(sum(1 for row in items if row["passed"] != "yes"))
    x = range(len(categories))
    plt.figure(figsize=(8, 4.2), dpi=150)
    plt.bar(x, passed, color="#2e7d32", label="已拦截/安全处理")
    plt.bar(x, failed, bottom=passed, color="#c62828", label="未通过")
    plt.xticks(list(x), [SECURITY_LABELS[item] for item in categories])
    plt.ylabel("用例数")
    plt.title("安全测试结果")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_3_security.png")
    plt.close()


def chart_api(rows: list[dict[str, str]]) -> None:
    labels = [ENDPOINT_LABELS.get(row["endpoint"], row["endpoint"]) for row in rows]
    x = list(range(len(labels)))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=150)
    ax.bar([value - width / 2 for value in x], [float(row["p50"]) for row in rows], width=width, color="#1565c0", label="P50")
    ax.bar([value + width / 2 for value in x], [float(row["p95"]) for row in rows], width=width, color="#ef6c00", label="P95")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel("响应时间（毫秒）")
    ax.set_title("接口响应时间")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4a_api_latency.png")
    plt.close()


def chart_concurrency(rows: list[dict[str, str]]) -> None:
    x = [int(row["parallel"]) for row in rows]
    success = [float(row["success_rate_percent"]) for row in rows]
    avg = [float(row["avg_response_ms"]) for row in rows]
    fig, ax1 = plt.subplots(figsize=(8, 4.4), dpi=150)
    ax1.plot(x, success, marker="o", color="#2e7d32", label="创建成功率")
    ax1.set_xlabel("并发提交数")
    ax1.set_ylabel("成功率（%）", color="#2e7d32")
    ax1.set_ylim(0, 105)
    ax1.set_xticks(x)
    ax1.grid(axis="y", linestyle="--", alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(x, avg, marker="s", color="#1565c0", label="平均响应时间")
    ax2.set_ylabel("平均响应时间（毫秒）", color="#1565c0")
    fig.suptitle("并发任务创建能力")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_6_4c_concurrency.png")
    plt.close(fig)


def chart_compat(rows: list[dict[str, str]]) -> None:
    measured = [row for row in rows if row.get("measured") != "no"]
    if not measured:
        return
    labels = [row["asset"] for row in measured]
    sizes = [int(row["bytes"]) / 1024 for row in measured]
    plt.figure(figsize=(8, 4.2), dpi=150)
    plt.bar(range(len(labels)), sizes, color="#546e7a")
    plt.xticks(range(len(labels)), labels, rotation=20, ha="right")
    plt.ylabel("文件大小（KB）")
    plt.title("前端构建产物大小")
    plt.tight_layout()
    plt.savefig(FIGURES / "fig_6_4d_compat_assets.png")
    plt.close()


def redraw_charts_from_csv() -> None:
    chart_functional(read_csv(FIGURES / "test_functional.csv"))
    chart_security(read_csv(FIGURES / "test_security.csv"))
    chart_api(read_csv(FIGURES / "test_perf_api.csv"))
    chart_scan(read_csv(FIGURES / "test_perf_scan.csv"))
    chart_concurrency(read_csv(FIGURES / "test_perf_concurrency.csv"))
    chart_compat(read_csv(FIGURES / "test_compat_assets.csv"))


def env_info() -> dict[str, Any]:
    docker = "not available"
    try:
        docker = subprocess.check_output(
            [r"C:\Program Files\Docker\Docker\resources\bin\docker.exe", "--version"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception:
        pass
    return {
        "OS": platform.platform(),
        "Python": platform.python_version(),
        "CPU": platform.processor() or platform.machine(),
        "Docker": docker,
        "Backend URL": "http://127.0.0.1:5000/api",
        "DAST target": DAST_TARGET,
    }


def write_summary() -> None:
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
    lines += [
        "",
        f"Functional verification covered {total_func} module-level cases; {passed_func} passed and {total_func - passed_func} failed in the final run.",
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
        f"Security checks blocked or safely handled {passed_sec} of {len(security)} cases.",
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
        f"The highest measured API P95 latency was {max_p95:.2f} ms.",
        "Figure: `fig_6_4a_api_latency.png`.",
        "",
        "### Scan Duration",
        "",
        "| Type | Runs | Mean duration ms | Median duration ms | Results |",
        "|---|---:|---:|---:|---|",
    ]
    for kind in ["SAST", "SCA", "DAST"]:
        group = [row for row in scan_rows if row["task_type"] == kind]
        values = [float(row["duration_ms"]) for row in group]
        result_counts = {}
        for row in group:
            result_counts[row["result"]] = result_counts.get(row["result"], 0) + 1
        lines.append(
            f"| {kind} | {len(values)} | {statistics.mean(values):.2f} | {statistics.median(values):.2f} | `{json.dumps(result_counts, ensure_ascii=False)}` |"
        )
    lines += [
        "",
        "Scan durations were refreshed by invoking the real scanner services after the fixes.",
        "Figure: `fig_6_4b_scan_duration.png`.",
        "",
        "### Concurrency",
        "",
        "| Parallel | Submitted | Created | Success rate % | Avg response ms | Status counts |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for row in concurrency:
        lines.append(f"| {row['parallel']} | {row['submitted']} | {row['created']} | {row['success_rate_percent']} | {row['avg_response_ms']} | `{row['status_counts']}` |")
    lines += [
        "",
        f"At {max_parallel['parallel']} concurrent submissions, task creation success rate was {max_parallel['success_rate_percent']}% and average response time was {max_parallel['avg_response_ms']} ms; all {max_parallel['created']} created responses returned HTTP 201 in this run.",
        "Figure: `fig_6_4c_concurrency.png`.",
        "",
        "## Compatibility Asset Loading",
        "",
        "| Asset | Bytes | Read/download ms | Measured | Note |",
        "|---|---:|---:|---|---|",
    ]
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
        "- Initial failures were traced to stale smoke scripts, HTTP 429 being wrapped as 500, empty-file upload validation, and concurrent `user_task_no` allocation. These were fixed before the final data refresh.",
        "- Requested routes `/api/metrics/dashboard` and `/api/tasks/{id}/report?format=pdf` were not present; measured equivalents were `/api/admin/dashboard` and `/api/sast/tasks/{id}/export?format=pdf`.",
        "- Browser GUI timing values are intentionally left for local browser measurement instead of being fabricated from command-line asset reads.",
    ]
    (FIGURES / "THESIS_TEST_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    FIGURES.mkdir(exist_ok=True)
    RAW_LOGS.mkdir(exist_ok=True)
    configure_plot_style()
    if "--charts-only" in sys.argv:
        redraw_charts_from_csv()
        return 0
    functional = refresh_functional()
    chart_functional(functional)
    scan_rows = refresh_scan_rows()
    chart_scan(scan_rows)
    write_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
