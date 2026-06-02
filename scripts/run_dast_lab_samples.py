#!/usr/bin/env python3
"""Run authorized DAST lab targets repeatedly and write experiment summaries."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

try:
    from scripts import ci_security_scan as ci
except ImportError:  # pragma: no cover - supports direct execution from scripts/
    import ci_security_scan as ci

TERMINAL_SUCCESS = {"SUCCESS"}
TERMINAL_FAILURE = {"FAILED", "TIMEOUT", "CANCELLED"}


def load_targets(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("targets file must contain a JSON array")
    targets: list[dict] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict) or not item.get("name") or not item.get("url"):
            raise ValueError(f"target #{index} must include name and url")
        targets.append(
            {
                "name": str(item["name"]),
                "url": str(item["url"]),
                "description": str(item.get("description") or item["name"]),
            }
        )
    return targets


def create_dast_task(args, token: str, target: dict, round_no: int) -> int:
    payload = ci.post_json(
        args.base_url,
        "/dast/tasks",
        {
            "task_name": f"{target['name']}-dast-r{round_no}",
            "target_url": target["url"],
            "description": target["description"],
            "timeout": args.scan_timeout,
            "authorization_confirmed": True,
        },
        token,
    )
    task = payload.get("data", {}).get("task") or {}
    if not task.get("id"):
        raise ci.ApiError("create DAST task response did not include task.id")
    return int(task["id"])


def wait_for_dast_task(args, token: str, task_id: int) -> dict:
    deadline = time.time() + args.wait_timeout
    last_payload = {}
    while time.time() < deadline:
        last_payload = ci.get_json(args.base_url, f"/dast/tasks/{task_id}", token)
        task = last_payload.get("data", {}).get("task") or {}
        status = task.get("status")
        if status in TERMINAL_SUCCESS or status in TERMINAL_FAILURE:
            return last_payload
        time.sleep(args.poll_interval)
    raise TimeoutError(f"Task {task_id} did not finish within {args.wait_timeout}s")


def _top_types(type_distribution: dict) -> str:
    items = sorted(type_distribution.items(), key=lambda item: (-int(item[1] or 0), item[0]))
    return "; ".join(f"{name}={count}" for name, count in items[:5])


def build_summary_rows(results: list[dict]) -> list[dict]:
    rows = []
    for item in results:
        payload = item["payload"]
        task = payload.get("data", {}).get("task") or {}
        result = payload.get("data", {}).get("result") or {}
        severity = result.get("severity_distribution") or {}
        type_distribution = result.get("type_distribution") or {}
        report_path = Path(item["report_path"])
        rows.append(
            {
                "target": item["target"]["name"],
                "url": item["target"]["url"],
                "round": item["round"],
                "task_id": task.get("id"),
                "status": task.get("status"),
                "duration_ms": task.get("duration_ms") or 0,
                "crawled_pages": result.get("crawled_pages") or 0,
                "issue_count": result.get("issue_count") or 0,
                "critical": severity.get("CRITICAL", 0),
                "high": severity.get("HIGH", 0),
                "medium": severity.get("MEDIUM", 0),
                "low": severity.get("LOW", 0),
                "top_types": _top_types(type_distribution),
                "report": str(report_path),
            }
        )
    return rows


def write_markdown(rows: list[dict], path: Path) -> None:
    headers = [
        "靶场",
        "轮次",
        "状态",
        "耗时 ms",
        "爬取页面",
        "问题数",
        "严重",
        "高危",
        "中危",
        "低危",
        "主要类型",
        "报告",
    ]
    lines = [
        "# DAST Lab Sample Summary",
        "",
        "| " + " | ".join(headers) + " |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["target"]),
                    str(row["round"]),
                    str(row["status"]),
                    str(row["duration_ms"]),
                    str(row["crawled_pages"]),
                    str(row["issue_count"]),
                    str(row["critical"]),
                    str(row["high"]),
                    str(row["medium"]),
                    str(row["low"]),
                    str(row["top_types"] or "-"),
                    str(row["report"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args) -> list[dict]:
    token = ci.login(args)
    targets = load_targets(Path(args.targets_file))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for round_no in range(1, args.rounds + 1):
        for target in targets:
            task_id = create_dast_task(args, token, target, round_no)
            payload = wait_for_dast_task(args, token, task_id)
            report_path = out_dir / f"{target['name']}_r{round_no}_dast_{task_id}.json"
            try:
                report_path.write_bytes(ci.download_bytes(args.base_url, f"/dast/tasks/{task_id}/report", token))
            except ci.ApiError:
                report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append({"target": target, "round": round_no, "payload": payload, "report_path": report_path})

    rows = build_summary_rows(results)
    (out_dir / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(rows, out_dir / "summary.md")
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repeated authorized DAST lab samples")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--targets-file", default="主文档层/dast_targets.local.json")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--scan-timeout", type=int, default=180)
    parser.add_argument("--wait-timeout", type=int, default=360)
    parser.add_argument("--poll-interval", type=int, default=3)
    parser.add_argument("--out-dir", default="tmp/dast-lab-samples")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        rows = run(args)
        print(f"Wrote {len(rows)} DAST sample row(s) to {args.out_dir}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
