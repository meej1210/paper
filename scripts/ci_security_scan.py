#!/usr/bin/env python3
"""Call the DevSecOps platform from a CI job and enforce a small quality gate."""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from urllib import error, request

TERMINAL_SUCCESS = {"SUCCESS"}
TERMINAL_FAILURE = {"FAILED", "TIMEOUT", "CANCELLED"}


class ApiError(RuntimeError):
    pass


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _read_json(response) -> dict:
    return json.loads(response.read().decode("utf-8"))


def post_json(base_url: str, path: str, payload: dict, token: str | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(_url(base_url, path), data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=30) as resp:
            return _read_json(resp)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"POST {path} failed: HTTP {exc.code} {detail}") from exc


def get_json(base_url: str, path: str, token: str) -> dict:
    req = request.Request(_url(base_url, path), headers={"Authorization": f"Bearer {token}"})
    try:
        with request.urlopen(req, timeout=30) as resp:
            return _read_json(resp)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"GET {path} failed: HTTP {exc.code} {detail}") from exc


def download_bytes(base_url: str, path: str, token: str) -> bytes:
    req = request.Request(_url(base_url, path), headers={"Authorization": f"Bearer {token}"})
    try:
        with request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"download {path} failed: HTTP {exc.code} {detail}") from exc


def post_multipart(base_url: str, path: str, file_path: Path, fields: dict, token: str) -> dict:
    boundary = f"----devsecops-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8"))
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8")
    )
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    body = b"".join(chunks)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = request.Request(_url(base_url, path), data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=60) as resp:
            return _read_json(resp)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"POST {path} failed: HTTP {exc.code} {detail}") from exc


def login(args) -> str:
    payload = post_json(args.base_url, "/auth/login", {"username": args.username, "password": args.password})
    token = payload.get("data", {}).get("access_token")
    if not token:
        raise ApiError("login response did not include access_token")
    return token


def create_task(args, token: str) -> int:
    target = Path(args.target_file).resolve()
    if not target.exists():
        raise ApiError(f"target file not found: {target}")
    if args.type == "sast":
        payload = post_multipart(args.base_url, "/sast/tasks", target, {"task_name": "ci-sast", "scanner_engine": "bandit"}, token)
    else:
        payload = post_multipart(args.base_url, "/sca/tasks", target, {"task_name": "ci-sca"}, token)
    task = payload.get("data", {}).get("task") or {}
    if not task.get("id"):
        raise ApiError("create task response did not include task.id")
    return int(task["id"])


def wait_for_task(args, token: str, task_id: int) -> dict:
    detail_path = f"/{args.type}/tasks/{task_id}"
    deadline = time.time() + args.timeout
    last_payload = {}
    while time.time() < deadline:
        last_payload = get_json(args.base_url, detail_path, token)
        task = last_payload.get("data", {}).get("task") or {}
        status = task.get("status")
        if status in TERMINAL_SUCCESS:
            return last_payload
        if status in TERMINAL_FAILURE:
            raise SystemExit(2)
        time.sleep(3)
    print(f"Task {task_id} did not finish within {args.timeout}s", file=sys.stderr)
    raise SystemExit(2)


def issue_severity(issue: dict) -> str:
    return str(issue.get("issue_severity") or issue.get("severity") or issue.get("level") or "UNKNOWN").upper()


def gate_failed(args, payload: dict) -> tuple[bool, str]:
    issues = payload.get("data", {}).get("issues") or []
    if args.fail_on == "any":
        return bool(issues), f"{len(issues)} issue(s) found"
    if args.fail_on == "high":
        count = sum(1 for issue in issues if issue_severity(issue) in {"HIGH", "CRITICAL"})
        return count > 0, f"{count} high/critical issue(s) found"
    if args.fail_on == "fixable":
        count = sum(1 for issue in issues if issue.get("fix_versions"))
        return count > 0, f"{count} fixable dependency issue(s) found"
    return False, "quality gate disabled"


def write_outputs(args, task_id: int, payload: dict, report_bytes: bytes, gate_message: str) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{args.type}_report_{task_id}.json"
    summary_path = out_dir / f"{args.type}_summary_{task_id}.md"
    report_path.write_bytes(report_bytes)
    task = payload.get("data", {}).get("task") or {}
    issues = payload.get("data", {}).get("issues") or []
    summary_path.write_text(
        "\n".join(
            [
                f"# CI Security Scan Summary #{task_id}",
                "",
                f"- Type: {args.type.upper()}",
                f"- Status: {task.get('status', '-')}",
                f"- Issues: {len(issues)}",
                f"- Gate: {args.fail_on}",
                f"- Gate result: {gate_message}",
                f"- Report: {report_path}",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Report saved to {report_path}")
    print(f"Summary saved to {summary_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a DevSecOps CI security scan")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. http://127.0.0.1:5000/api")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--type", choices=["sast", "sca"], required=True)
    parser.add_argument("--target-file", required=True)
    parser.add_argument("--fail-on", choices=["high", "fixable", "any"], default="high")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out-dir", default="tmp/ci-artifacts")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        token = login(args)
        task_id = create_task(args, token)
        payload = wait_for_task(args, token, task_id)
        report_bytes = download_bytes(args.base_url, f"/{args.type}/tasks/{task_id}/report", token)
        failed, gate_message = gate_failed(args, payload)
        write_outputs(args, task_id, payload, report_bytes, gate_message)
        if failed:
            print(f"Quality gate failed: {gate_message}", file=sys.stderr)
            return 3
        print(f"Quality gate passed: {gate_message}")
        return 0
    except SystemExit as exc:
        return int(exc.code)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
