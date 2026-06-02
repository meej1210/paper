#!/usr/bin/env python3
"""Submit several scan tasks concurrently and write a small experiment report."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import ci_security_scan as ci


def create_one(args, token: str, index: int) -> dict:
    started = time.perf_counter()
    try:
        if args.type in {"sast", "sca"}:
            child = argparse.Namespace(**vars(args))
            task_id = ci.create_task(child, token)
        else:
            payload = ci.post_json(
                args.base_url,
                "/dast/tasks",
                {
                    "task_name": f"probe-dast-{index}",
                    "target_url": args.target_url,
                    "timeout": args.scan_timeout,
                    "authorization_confirmed": True,
                },
                token,
            )
            task_id = int(payload["data"]["task"]["id"])
        elapsed = int((time.perf_counter() - started) * 1000)
        return {"index": index, "created": True, "task_id": task_id, "response_ms": elapsed, "error": ""}
    except Exception as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return {"index": index, "created": False, "task_id": "", "response_ms": elapsed, "error": str(exc)}


def poll_final(args, token: str, task_id: int) -> str:
    detail_type = args.type
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        payload = ci.get_json(args.base_url, f"/{detail_type}/tasks/{task_id}", token)
        status = payload.get("data", {}).get("task", {}).get("status", "UNKNOWN")
        if status in ci.TERMINAL_SUCCESS | ci.TERMINAL_FAILURE:
            return status
        time.sleep(3)
    return "TIMEOUT"


def write_report(args, rows: list[dict]) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"concurrency_{args.type}_{args.count}.csv"
    md_path = out_dir / f"concurrency_{args.type}_{args.count}.md"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["index", "created", "task_id", "response_ms", "final_status", "error"])
        writer.writeheader()
        writer.writerows(rows)
    created = [row for row in rows if row["created"]]
    response_times = [int(row["response_ms"]) for row in rows]
    status_counts = {}
    for row in rows:
        status_counts[row.get("final_status") or "CREATE_FAILED"] = status_counts.get(row.get("final_status") or "CREATE_FAILED", 0) + 1
    md_path.write_text(
        "\n".join(
            [
                f"# Concurrency Probe - {args.type.upper()}",
                "",
                f"- Submitted tasks: {args.count}",
                f"- Parallelism: {args.parallel}",
                f"- Created successfully: {len(created)}",
                f"- Create failures: {args.count - len(created)}",
                f"- Average response time(ms): {int(statistics.mean(response_times)) if response_times else 0}",
                f"- Final status distribution: {json.dumps(status_counts, ensure_ascii=False)}",
                f"- CSV: {csv_path}",
            ]
        ),
        encoding="utf-8",
    )
    print(f"CSV saved to {csv_path}")
    print(f"Markdown saved to {md_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a limited concurrency probe")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--type", choices=["sast", "sca", "dast"], required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--parallel", type=int, default=5)
    parser.add_argument("--target-file", default="")
    parser.add_argument("--target-url", default="http://127.0.0.1:3000")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--scan-timeout", type=int, default=60)
    parser.add_argument("--fail-on", default="high")
    parser.add_argument("--out-dir", default="tmp/concurrency-artifacts")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.type in {"sast", "sca"} and not args.target_file:
        print("--target-file is required for sast/sca probes", file=sys.stderr)
        return 1
    try:
        token = ci.login(args)
        rows = []
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = [pool.submit(create_one, args, token, index) for index in range(1, args.count + 1)]
            for future in as_completed(futures):
                rows.append(future.result())
        for row in rows:
            if row["created"]:
                row["final_status"] = poll_final(args, token, int(row["task_id"]))
            else:
                row["final_status"] = "CREATE_FAILED"
        rows.sort(key=lambda item: item["index"])
        write_report(args, rows)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
