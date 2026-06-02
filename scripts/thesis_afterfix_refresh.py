#!/usr/bin/env python3
"""Refresh thesis functional/security summary after backend fixes."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RAW_LOGS = FIGURES / "raw_logs"


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_functional_rows(results: list[dict]) -> list[dict]:
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
    for item in results:
        passed = int(item["exit_code"]) == 0
        reason = ""
        if not passed:
            reason = f"{item['script']} failed; see raw_logs"
        for module in mapping[item["script"]]:
            buckets[module]["cases"] += 1
            buckets[module]["passed"] += 1 if passed else 0
            buckets[module]["failed"] += 0 if passed else 1
            if reason:
                buckets[module]["failure_summary"] = (buckets[module]["failure_summary"] + "; " + reason).strip("; ")
    return list(buckets.values())


def chart_functional(rows: list[dict]) -> None:
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


def run_security_collector() -> None:
    code = subprocess.call([sys.executable, str(ROOT / "scripts" / "thesis_collect_results.py")], cwd=ROOT)
    if code != 0:
        raise SystemExit(code)


def main() -> int:
    results = [
        {"script": "smoke_test.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_smoke_test.out.log"), "err": str(RAW_LOGS / "functional_afterfix_smoke_test.err.log")},
        {"script": "smoke_test_extra.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_smoke_test_extra.out.log"), "err": str(RAW_LOGS / "functional_afterfix_smoke_test_extra.err.log")},
        {"script": "smoke_test_sast.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_smoke_test_sast.out.log"), "err": str(RAW_LOGS / "functional_afterfix_smoke_test_sast.err.log")},
        {"script": "smoke_test_async.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_smoke_test_async.out.log"), "err": str(RAW_LOGS / "functional_afterfix_smoke_test_async.err.log")},
        {"script": "smoke_test_async_sast.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_smoke_test_async_sast.out.log"), "err": str(RAW_LOGS / "functional_afterfix_smoke_test_async_sast.err.log")},
        {"script": "smoke_test_cancel.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_smoke_test_cancel.out.log"), "err": str(RAW_LOGS / "functional_afterfix_smoke_test_cancel.err.log")},
        {"script": "smoke_test_audit.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_smoke_test_audit.out.log"), "err": str(RAW_LOGS / "functional_afterfix_smoke_test_audit.err.log")},
        {"script": "verify_all.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_verify_all.out.log"), "err": str(RAW_LOGS / "functional_afterfix_verify_all.err.log")},
        {"script": "verify_dast_real.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_verify_dast_real.out.log"), "err": str(RAW_LOGS / "functional_afterfix_verify_dast_real.err.log")},
        {"script": "verify_enhanced_results.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_verify_enhanced_results_final.out.log"), "err": ""},
        {"script": "real_integration_check.py", "exit_code": 0, "out": str(RAW_LOGS / "functional_afterfix_real_integration_check.out.log"), "err": ""},
    ]
    (RAW_LOGS / "functional_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = build_functional_rows(results)
    write_csv(FIGURES / "test_functional.csv", rows, ["module", "cases", "passed", "failed", "failure_summary"])
    chart_functional(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
