import io
import json
from datetime import UTC, datetime

import pytest

from app.models import Task, TaskStatus, TaskType, User
from app.services.dast_service import _build_wapiti_command
from tests.conftest import _auth_headers as auth_headers


def _create_sast_task(client, user_id, filename="test.py", content="print('hello')", **extra_form):
    data = {"file": (io.BytesIO(content.encode()), filename), **extra_form}
    return client.post("/api/sast/tasks", data=data, headers=auth_headers(user_id), content_type="multipart/form-data")


class TestSastTaskCreation:
    def test_create_sast_no_file(self, client, sample_user):
        response = client.post("/api/sast/tasks", headers=auth_headers(sample_user.id))
        assert response.status_code == 400

    def test_create_sast_unsupported_extension(self, client, sample_user):
        data = {"file": (io.BytesIO(b"content"), "malware.exe")}
        response = client.post(
            "/api/sast/tasks",
            data=data,
            headers=auth_headers(sample_user.id),
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_create_sast_rejects_empty_file(self, client, sample_user):
        data = {"file": (io.BytesIO(b""), "empty.py")}
        response = client.post(
            "/api/sast/tasks",
            data=data,
            headers=auth_headers(sample_user.id),
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert response.get_json()["errors"]["file"] == "empty file"

    def test_create_sast_success(self, client, sample_user):
        response = _create_sast_task(client, sample_user.id)
        assert response.status_code == 201
        data = response.get_json()
        task = data["data"]["task"]
        assert task["user_task_no"] == 1
        assert task["task_type"] == "SAST"
        assert task["scanner_engine"] == "bandit"
        assert task["status"] in ("PENDING", "RUNNING", "SUCCESS", "FAILED")
        assert "target_name" in task
        assert "target_path" not in task

    def test_create_sast_with_semgrep_engine(self, client, sample_user, monkeypatch):
        monkeypatch.setattr("app.api.sast.execute_sast_task", lambda task_id: None)
        response = _create_sast_task(client, sample_user.id, scanner_engine="semgrep")
        assert response.status_code == 201
        task = response.get_json()["data"]["task"]
        assert task["scanner_engine"] == "semgrep"
        assert task["status"] == "PENDING"

    def test_create_sast_invalid_engine(self, client, sample_user):
        response = _create_sast_task(client, sample_user.id, scanner_engine="bad-engine")
        assert response.status_code == 400
        errors = response.get_json()["errors"]
        assert errors["scanner_engine"] == "invalid value"

    def test_create_sast_no_auth(self, client):
        data = {"file": (io.BytesIO(b"print('x')"), "test.py")}
        response = client.post("/api/sast/tasks", data=data, content_type="multipart/form-data")
        assert response.status_code == 401


class TestDastTaskCreation:
    def test_create_dast_success(self, client, sample_user):
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "http://127.0.0.1:3000", "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["data"]["task"]["task_type"] == "DAST"
        assert data["data"]["task"]["status"] in ("PENDING", "RUNNING", "SUCCESS", "FAILED", "TIMEOUT")

    def test_create_dast_invalid_url(self, client, sample_user):
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "ftp://bad.scheme.com", "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 400

    def test_create_dast_public_url_blocked(self, client, sample_user):
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "http://example.com", "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 400

    def test_create_dast_public_url_allowed_when_public_mode_enabled(self, app, client, sample_user, monkeypatch):
        app.config["DAST_ALLOW_PUBLIC_TARGETS"] = True
        app.config["DAST_ALLOWED_HOSTS"] = ("127.0.0.1", "localhost")
        monkeypatch.setattr("app.api.dast.execute_dast_task", lambda task_id: None)
        monkeypatch.setattr("app.utils.validators._resolve_target_ip", lambda hostname: "110.242.68.3")
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "https://www.baidu.com/", "authorization_confirmed": True, "timeout": 300},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 201
        task = response.get_json()["data"]["task"]
        assert task["target_host"] == "www.baidu.com"
        assert task["target_ip"] == "110.242.68.3"
        assert task["target_policy"] == "public_allowed"
        assert task["timeout_seconds"] == 60

    def test_create_dast_public_mode_still_requires_authorization_confirmation(self, app, client, sample_user):
        app.config["DAST_ALLOW_PUBLIC_TARGETS"] = True
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "https://www.baidu.com/"},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 400
        assert response.get_json()["errors"]["authorization_confirmed"] == "required"

    def test_create_dast_baidu_allowed_by_explicit_host(self, app, client, sample_user, monkeypatch):
        app.config["DAST_ALLOWED_HOSTS"] = ("127.0.0.1", "localhost", "www.baidu.com", "baidu.com")
        monkeypatch.setattr("app.api.dast.execute_dast_task", lambda task_id: None)
        monkeypatch.setattr("app.utils.validators._resolve_target_ip", lambda hostname: "110.242.68.3")
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "https://www.baidu.com/", "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 201
        task = response.get_json()["data"]["task"]
        assert task["target_host"] == "www.baidu.com"
        assert task["target_policy"] == "allowed_host"

    def test_create_dast_allows_explicit_public_host(self, app, client, sample_user, monkeypatch):
        app.config["DAST_ALLOWED_HOSTS"] = ("authorized.example.test",)
        monkeypatch.setattr("app.api.dast.execute_dast_task", lambda task_id: None)
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "https://authorized.example.test", "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 201
        task = response.get_json()["data"]["task"]
        assert task["target_host"] == "authorized.example.test"
        assert task["target_policy"] == "allowed_host"


    def test_create_dast_requires_authorization_confirmation(self, client, sample_user):
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "http://127.0.0.1:3000"},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 400
        errors = response.get_json()["errors"]
        assert errors["authorization_confirmed"] == "required"

    def test_create_dast_records_authorization_context(self, client, sample_user, db):
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "http://127.0.0.1:3000", "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 201
        task_id = response.get_json()["data"]["task"]["id"]
        task = db.session.get(Task, task_id)
        assert task.authorization_confirmed is True
        assert task.target_host == "127.0.0.1"
        assert task.target_ip == "127.0.0.1"
        assert task.target_policy == "localhost"
        assert response.get_json()["data"]["task"]["target_policy"] == "localhost"

    def test_create_dast_public_auth_audit_log_contains_request_context(self, app, client, sample_user, db, monkeypatch):
        from app.models import AuditLog

        app.config["DAST_ALLOW_PUBLIC_TARGETS"] = True
        app.config["DAST_ALLOWED_HOSTS"] = ("127.0.0.1", "localhost")
        monkeypatch.setattr("app.api.dast.execute_dast_task", lambda task_id: None)
        monkeypatch.setattr("app.utils.validators._resolve_target_ip", lambda hostname: "110.242.68.3")
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "https://www.baidu.com/", "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
            environ_base={"REMOTE_ADDR": "203.0.113.9"},
        )
        assert response.status_code == 201
        task_id = response.get_json()["data"]["task"]["id"]
        log = AuditLog.query.filter_by(action="DAST_AUTH_CONFIRMED", resource_id=str(task_id)).first()
        detail = json.loads(log.detail)
        assert log.user_id == sample_user.id
        assert log.ip_address == "203.0.113.9"
        assert detail["target_host"] == "www.baidu.com"
        assert detail["target_ip"] == "110.242.68.3"
        assert detail["target_policy"] == "public_allowed"
        assert detail["authorization_confirmed"] is True

    def test_create_dast_audit_log_contains_authorization_detail(self, client, sample_user, db):
        from app.models import AuditLog

        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "http://127.0.0.1:3000", "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 201
        task_id = response.get_json()["data"]["task"]["id"]
        log = AuditLog.query.filter_by(resource_type="task", resource_id=str(task_id)).order_by(AuditLog.id.desc()).first()
        detail = json.loads(log.detail)
        assert detail["target_url"] == "http://127.0.0.1:3000"
        assert detail["authorization_confirmed"] is True
        assert detail["policy"] == "localhost"

    def test_create_dast_no_auth(self, client):
        response = client.post("/api/dast/tasks", json={"target_url": "http://127.0.0.1:3000"})
        assert response.status_code == 401

    def test_create_dast_timeout_validation(self, client, sample_user):
        response = client.post(
            "/api/dast/tasks",
            json={"target_url": "http://127.0.0.1:3000", "timeout": 99999, "authorization_confirmed": True},
            headers=auth_headers(sample_user.id),
        )
        assert response.status_code == 400


class TestDastScannerCommand:
    def test_allowed_public_host_uses_public_low_intensity_limits(self, app, tmp_path):
        app.config["DAST_PUBLIC_SCOPE"] = "url"
        app.config["DAST_PUBLIC_MAX_SCAN_TIME"] = 20
        app.config["DAST_PUBLIC_MAX_ATTACK_TIME"] = 5
        app.config["DAST_PUBLIC_REQUEST_TIMEOUT"] = 3
        task = Task(
            user_id=1,
            task_type=TaskType.DAST,
            target_url="https://www.baidu.com/",
            timeout_seconds=60,
            target_host="www.baidu.com",
            target_ip="103.235.46.102",
            target_policy="allowed_host",
        )

        command = _build_wapiti_command(task, tmp_path / "dast.json")

        assert command[command.index("--scope") + 1] == "url"
        assert command[command.index("--max-scan-time") + 1] == "20"
        assert command[command.index("--max-attack-time") + 1] == "5"
        assert command[command.index("-t") + 1] == "3"

    def test_public_target_uses_low_intensity_limits(self, app, tmp_path):
        app.config["DAST_MAX_SCAN_TIME"] = 60
        app.config["DAST_MAX_ATTACK_TIME"] = 15
        app.config["DAST_PUBLIC_SCOPE"] = "url"
        app.config["DAST_PUBLIC_MAX_SCAN_TIME"] = 20
        app.config["DAST_PUBLIC_MAX_ATTACK_TIME"] = 5
        app.config["DAST_PUBLIC_REQUEST_TIMEOUT"] = 3
        task = Task(
            user_id=1,
            task_type=TaskType.DAST,
            target_url="https://www.baidu.com/",
            timeout_seconds=300,
            target_policy="public_allowed",
        )

        command = _build_wapiti_command(task, tmp_path / "dast.json")

        assert command[command.index("--scope") + 1] == "url"
        assert command[command.index("--max-scan-time") + 1] == "20"
        assert command[command.index("--max-attack-time") + 1] == "5"
        assert command[command.index("-t") + 1] == "3"


class TestTaskList:
    def test_list_tasks_empty(self, client, sample_user):
        response = client.get("/api/tasks", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["items"] == []
        assert data["data"]["pagination"]["total"] == 0

    def test_list_tasks_with_data(self, client, sample_user):
        _create_sast_task(client, sample_user.id)
        response = client.get("/api/tasks", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["pagination"]["total"] >= 1
        assert data["data"]["items"][0]["user_task_no"] >= 1

    def test_list_tasks_returns_chinese_summary_and_beijing_time(self, client, sample_user, db):
        task = Task(
            user_id=sample_user.id,
            task_type=TaskType.DAST,
            status=TaskStatus.SUCCESS,
            target_url="http://127.0.0.1:3000/",
            result_summary=(
                "Wapiti scan completed for http://127.0.0.1:3000/: "
                "3 vulnerabilities, 0 anomalies, 0 additional findings, 1 crawled pages"
            ),
            created_at=datetime(2026, 5, 27, 7, 10, 28, tzinfo=UTC),
        )
        db.session.add(task)
        db.session.commit()

        response = client.get("/api/tasks", headers=auth_headers(sample_user.id))

        assert response.status_code == 200
        item = response.get_json()["data"]["items"][0]
        assert item["result_summary"] == "Wapiti 扫描完成：http://127.0.0.1:3000/，发现 3 个漏洞、0 个异常、0 个附加发现，爬取 1 个页面"
        assert item["created_at"] == "2026-05-27T15:10:28+08:00"

    def test_user_task_no_increments_per_user(self, client, sample_user, db):
        _create_sast_task(client, sample_user.id, filename="first.py")
        _create_sast_task(client, sample_user.id, filename="second.py")

        from app.utils.security import hash_password

        other = User(username="peruser", email="peruser@example.com", password_hash=hash_password("password123"))
        db.session.add(other)
        db.session.commit()

        _create_sast_task(client, other.id, filename="other.py")

        response = client.get("/api/tasks", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        items = response.get_json()["data"]["items"]
        user_numbers = sorted(item["user_task_no"] for item in items[:2])
        assert user_numbers == [1, 2]

        other_response = client.get("/api/tasks", headers=auth_headers(other.id))
        other_items = other_response.get_json()["data"]["items"]
        assert other_items[0]["user_task_no"] == 1

    def test_create_task_retries_user_task_no_collision(self, sample_user, db, monkeypatch):
        from sqlalchemy.exc import IntegrityError

        from app.services import task_service
        from app.services.task_service import create_task

        original_commit = db.session.commit
        calls = {"count": 0}

        def flaky_commit():
            calls["count"] += 1
            if calls["count"] == 1:
                raise IntegrityError("INSERT INTO tasks", {}, Exception("duplicate user_task_no"))
            return original_commit()

        monkeypatch.setattr(task_service.db.session, "commit", flaky_commit)

        task = create_task(user_id=sample_user.id, task_type=TaskType.SAST, target_path="/tmp/test.py")

        assert task.id is not None
        assert calls["count"] == 2

    def test_list_tasks_filter_by_type(self, client, sample_user):
        _create_sast_task(client, sample_user.id)
        response = client.get("/api/tasks?task_type=SAST", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        items = response.get_json()["data"]["items"]
        assert all(item["task_type"] == "SAST" for item in items)

    def test_list_tasks_filter_by_status(self, client, sample_user):
        response = client.get("/api/tasks?status=SUCCESS", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        items = response.get_json()["data"]["items"]
        assert all(item["status"] == "SUCCESS" for item in items)

    def test_list_tasks_pagination(self, client, sample_user):
        response = client.get("/api/tasks?page=1&page_size=5", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["pagination"]["page_size"] == 5

    def test_list_tasks_no_auth(self, client):
        response = client.get("/api/tasks")
        assert response.status_code == 401


class TestTaskCancel:
    def test_cancel_pending_task(self, client, sample_user, db):
        task = Task(user_id=sample_user.id, task_type=TaskType.SAST, status=TaskStatus.PENDING)
        db.session.add(task)
        db.session.commit()

        response = client.post(f"/api/tasks/{task.id}/cancel", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        assert response.get_json()["data"]["status"] == "CANCELLED"

    def test_cancel_completed_task_fails(self, client, sample_user, db):
        task = Task(user_id=sample_user.id, task_type=TaskType.SAST, status=TaskStatus.SUCCESS)
        db.session.add(task)
        db.session.commit()

        response = client.post(f"/api/tasks/{task.id}/cancel", headers=auth_headers(sample_user.id))
        assert response.status_code == 400

    def test_cancel_other_users_task(self, client, sample_user, db):
        from app.utils.security import hash_password

        other = User(username="other", email="other@example.com", password_hash=hash_password("password123"))
        db.session.add(other)
        db.session.commit()

        task = Task(user_id=other.id, task_type=TaskType.SAST, status=TaskStatus.PENDING)
        db.session.add(task)
        db.session.commit()

        response = client.post(f"/api/tasks/{task.id}/cancel", headers=auth_headers(sample_user.id))
        assert response.status_code == 404


class TestTaskRerun:
    def test_rerun_success(self, client, sample_user, db):
        task = Task(
            user_id=sample_user.id,
            task_type=TaskType.SAST,
            status=TaskStatus.SUCCESS,
            target_path="/tmp/test.py",
            scanner_engine="semgrep",
        )
        db.session.add(task)
        db.session.commit()

        response = client.post(f"/api/tasks/{task.id}/rerun", headers=auth_headers(sample_user.id))
        assert response.status_code == 201
        data = response.get_json()
        assert data["data"]["original_task_id"] == task.id
        assert data["data"]["new_task"]["id"] != task.id
        assert data["data"]["new_task"]["user_task_no"] == task.user_task_no + 1
        assert data["data"]["new_task"]["scanner_engine"] == "semgrep"
