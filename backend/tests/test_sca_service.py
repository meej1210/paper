import json
import subprocess
import zipfile
from pathlib import Path

from app.models import ScaIssue, Task, TaskStatus, TaskType
from app.services.sca_service import build_pip_audit_command, locate_requirements_file, parse_pip_audit_report, run_pip_audit_scan
from app.workers.sca_tasks import execute_sca_task


def test_parse_pip_audit_report_with_vulns():
    payload = {
        "dependencies": [
            {
                "name": "django",
                "version": "2.2.0",
                "vulns": [
                    {
                        "id": "PYSEC-2021-9",
                        "aliases": ["CVE-2021-3281"],
                        "fix_versions": ["2.2.18"],
                        "description": "SQL injection vulnerability",
                    }
                ],
            },
            {"name": "requests", "version": "2.31.0", "vulns": []},
        ]
    }

    parsed = parse_pip_audit_report(payload)

    assert parsed["dependency_count"] == 2
    assert parsed["vulnerability_count"] == 1
    assert parsed["fixable_count"] == 1
    assert parsed["issues"][0]["package_name"] == "django"
    assert parsed["issues"][0]["installed_version"] == "2.2.0"
    assert parsed["issues"][0]["vulnerability_id"] == "PYSEC-2021-9"
    assert parsed["issues"][0]["aliases"] == ["CVE-2021-3281"]
    assert parsed["issues"][0]["fix_versions"] == ["2.2.18"]
    assert parsed["issues"][0]["severity"] == "HIGH"


def test_parse_pip_audit_report_without_vulns():
    parsed = parse_pip_audit_report({"dependencies": [{"name": "flask", "version": "3.0.0", "vulns": []}]})

    assert parsed["dependency_count"] == 1
    assert parsed["vulnerability_count"] == 0
    assert parsed["fixable_count"] == 0
    assert parsed["issues"] == []


def test_locate_requirements_file_from_txt(tmp_path):
    target = tmp_path / "requirements.txt"
    target.write_text("flask==3.0.0\n", encoding="utf-8")

    assert locate_requirements_file(str(target)) == str(target)


def test_locate_requirements_file_from_zip(tmp_path):
    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("app/requirements.txt", "django==2.2.0\n")

    located = locate_requirements_file(str(archive))

    assert Path(located).name == "requirements.txt"
    assert Path(located).read_text(encoding="utf-8") == "django==2.2.0\n"
    assert any(parent.name.startswith("sca_") for parent in Path(located).parents)


def test_build_pip_audit_command_uses_current_python_by_default(tmp_path):
    requirements_path = tmp_path / "requirements.txt"
    report_path = tmp_path / "report.json"

    command = build_pip_audit_command(None, str(requirements_path), report_path)

    assert command[1:3] == ["-m", "pip_audit"]
    assert command[3:] == [
        "-r",
        str(requirements_path),
        "--format",
        "json",
        "--output",
        str(report_path),
        "--disable-pip",
        "--no-deps",
    ]


def test_run_pip_audit_scan_persists_results(app, db, sample_user, monkeypatch, tmp_path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    app.config["REPORT_DIR"] = str(report_dir)

    target = tmp_path / "requirements.txt"
    target.write_text("django==2.2.0\n", encoding="utf-8")
    task = Task(user_id=sample_user.id, task_type=TaskType.SCA, status=TaskStatus.PENDING, target_path=str(target))
    db.session.add(task)
    db.session.commit()

    def fake_run(command, capture_output, text, encoding, errors, timeout, check):
        report_path = Path(command[command.index("--output") + 1])
        report_path.write_text(
            json.dumps(
                {
                    "dependencies": [
                        {
                            "name": "django",
                            "version": "2.2.0",
                            "vulns": [
                                {
                                    "id": "PYSEC-2021-9",
                                    "aliases": ["CVE-2021-3281"],
                                    "fix_versions": ["2.2.18"],
                                    "description": "SQL injection vulnerability",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="")

    monkeypatch.setattr("app.services.sca_service.subprocess.run", fake_run)

    run_pip_audit_scan(task)
    db.session.refresh(task)

    issue = ScaIssue.query.filter_by(task_id=task.id).one()
    assert task.status == TaskStatus.SUCCESS
    assert task.report_path == str(report_dir / f"sca_{task.id}.json")
    assert task.sca_result.dependency_count == 1
    assert task.sca_result.vulnerability_count == 1
    assert task.sca_result.fixable_count == 1
    assert issue.package_name == "django"
    assert issue.vulnerability_id == "PYSEC-2021-9"
    assert issue.aliases == json.dumps(["CVE-2021-3281"], ensure_ascii=False)


def test_run_pip_audit_scan_marks_failed_when_report_missing(app, db, sample_user, monkeypatch, tmp_path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    app.config["REPORT_DIR"] = str(report_dir)

    target = tmp_path / "requirements.txt"
    target.write_text("requests==2.19.1\nurllib3==1.24.1\n", encoding="utf-8")
    task = Task(user_id=sample_user.id, task_type=TaskType.SCA, status=TaskStatus.PENDING, target_path=str(target))
    db.session.add(task)
    db.session.commit()

    def fake_run(command, capture_output, text, encoding, errors, timeout, check):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="ResolutionImpossible")

    monkeypatch.setattr("app.services.sca_service.subprocess.run", fake_run)

    run_pip_audit_scan(task)
    db.session.refresh(task)

    assert task.status == TaskStatus.FAILED
    assert task.progress == 100
    assert task.result_summary == "pip-audit report parse failed"
    assert "report file was not generated" in (task.error_message or "")


def test_execute_sca_task_marks_failed_on_unexpected_error(app, db, sample_user, monkeypatch, tmp_path):
    target = tmp_path / "requirements.txt"
    target.write_text("flask==3.0.0\n", encoding="utf-8")
    task = Task(user_id=sample_user.id, task_type=TaskType.SCA, status=TaskStatus.PENDING, target_path=str(target))
    db.session.add(task)
    db.session.commit()

    def boom(current_task):
        raise RuntimeError("simulated sca failure")

    monkeypatch.setattr("app.services.sca_service.run_pip_audit_scan", boom)

    try:
        execute_sca_task(task.id)
    except RuntimeError:
        pass

    db.session.refresh(task)
    assert task.status == TaskStatus.FAILED
    assert task.progress == 100
    assert task.result_summary == "SCA 扫描异常失败"
    assert "simulated sca failure" in (task.error_message or "")
