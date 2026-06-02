import json
import subprocess
from pathlib import Path

from app.models import SastIssue, Task, TaskStatus, TaskType
from app.services.sast_service import run_semgrep_scan
from app.workers.sast_tasks import execute_sast_task


def test_execute_sast_task_routes_to_semgrep(app, db, sample_user, monkeypatch, tmp_path):
    target = tmp_path / "route_test.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    task = Task(
        user_id=sample_user.id,
        task_type=TaskType.SAST,
        status=TaskStatus.PENDING,
        target_path=str(target),
        scanner_engine="semgrep",
    )
    db.session.add(task)
    db.session.commit()

    calls: list[tuple[str, int]] = []
    monkeypatch.setattr("app.services.sast_service.run_semgrep_scan", lambda current_task: calls.append(("semgrep", current_task.id)))
    monkeypatch.setattr("app.services.sast_service.run_bandit_scan", lambda current_task: calls.append(("bandit", current_task.id)))

    execute_sast_task(task.id)

    assert calls == [("semgrep", task.id)]


def test_run_semgrep_scan_persists_results(app, db, sample_user, monkeypatch, tmp_path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    app.config["REPORT_DIR"] = str(report_dir)

    target = tmp_path / "semgrep_target.py"
    target.write_text(
        "import subprocess\n"
        "def run(cmd):\n"
        "    return subprocess.check_output(cmd, shell=True)\n",
        encoding="utf-8",
    )

    task = Task(
        user_id=sample_user.id,
        task_type=TaskType.SAST,
        status=TaskStatus.PENDING,
        target_path=str(target),
        scanner_engine="semgrep",
    )
    db.session.add(task)
    db.session.commit()

    def fake_run(command, capture_output, text, encoding, errors, check):
        report_path = Path(command[command.index("--output") + 1])
        payload = {
            "results": [
                {
                    "check_id": "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true",
                    "path": target.name,
                    "start": {"line": 3},
                    "end": {"line": 3},
                    "extra": {
                        "message": "shell=True is dangerous",
                        "severity": "ERROR",
                        "lines": "requires login",
                        "metadata": {
                            "confidence": "MEDIUM",
                            "cwe": [
                                "CWE-78: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')"
                            ],
                            "owasp": ["A03:2021 - Injection", "A01:2025 - Broken Access Control"],
                            "references": ["https://example.com/reference"],
                            "source": "https://semgrep.dev/r/test",
                            "shortlink": "https://sg.run/test",
                        },
                    },
                }
            ]
        }
        report_path.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("app.services.sast_service.subprocess.run", fake_run)

    run_semgrep_scan(task)
    db.session.refresh(task)

    issue = SastIssue.query.filter_by(task_id=task.id).one()

    assert task.status == TaskStatus.SUCCESS
    assert task.report_path == str(report_dir / f"sast_{task.id}.json")
    assert task.sast_result is not None
    assert task.sast_result.issue_count == 1
    assert task.sast_result.high_count == 1
    assert issue.test_id == "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true"
    assert len(issue.test_id) > 64
    assert issue.test_name == "https://sg.run/test"
    assert issue.issue_severity == "HIGH"
    assert issue.issue_confidence == "MEDIUM"
    assert issue.filename == str(target.resolve())
    assert issue.line_number == 3
    assert issue.code == "return subprocess.check_output(cmd, shell=True)"
    assert issue.cwe == "CWE-78"
    assert issue.owasp == "A03:2021-Injection"
    assert "https://semgrep.dev/r/test" in (issue.more_info or "")
    assert "https://example.com/reference" in (issue.more_info or "")


def test_execute_sast_task_marks_failed_on_unexpected_error(app, db, sample_user, monkeypatch, tmp_path):
    target = tmp_path / "unexpected_error.py"
    target.write_text("print('hello')\n", encoding="utf-8")

    task = Task(
        user_id=sample_user.id,
        task_type=TaskType.SAST,
        status=TaskStatus.PENDING,
        target_path=str(target),
        scanner_engine="semgrep",
    )
    db.session.add(task)
    db.session.commit()

    def boom(current_task):
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr("app.workers.sast_tasks.run_semgrep_scan", boom, raising=False)
    monkeypatch.setattr("app.services.sast_service.run_semgrep_scan", boom)

    try:
        execute_sast_task(task.id)
    except RuntimeError:
        pass

    db.session.refresh(task)
    assert task.status == TaskStatus.FAILED
    assert task.progress == 100
    assert task.result_summary == "SAST 扫描异常失败"
    assert "simulated persistence failure" in (task.error_message or "")
