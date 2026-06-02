import json
from datetime import UTC, datetime, timedelta

from tests.conftest import _auth_headers as auth_headers


class TestAuditLogs:
    def test_audit_logs_user_can_only_see_own_entries(self, client, db, sample_user, admin_user):
        from app.models import AuditLog

        db.session.add(
            AuditLog(
                user_id=sample_user.id,
                action="REPORT_VIEW",
                resource_type="task",
                resource_id="54",
                detail=json.dumps({"task_id": 54, "task_type": "SAST", "result": "success"}),
            )
        )
        db.session.add(
            AuditLog(
                user_id=admin_user.id,
                action="AUTH_LOGIN_SUCCESS",
                resource_type="user",
                resource_id=str(admin_user.id),
                detail=json.dumps({"result": "success"}),
            )
        )
        db.session.commit()

        response = client.get("/api/audit-logs", headers=auth_headers(sample_user.id))
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["pagination"]["total"] == 1
        assert data["items"][0]["user"]["id"] == sample_user.id
        assert data["items"][0]["report_route"] == "/tasks/54?type=SAST"

    def test_audit_logs_admin_access(self, client, admin_headers):
        response = client.get("/api/audit-logs", headers=admin_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data["data"]
        assert "pagination" in data["data"]
        assert "summary" in data["data"]
        assert "charts" in data["data"]

    def test_audit_logs_no_auth(self, client):
        response = client.get("/api/audit-logs")
        assert response.status_code == 401

    def test_audit_log_created_on_register(self, client, admin_headers, db):
        from app.models import AuditLog

        client.post("/api/auth/register", json={"username": "audit_test", "email": "audit@test.com", "password": "password123"})

        logs = AuditLog.query.filter_by(action="REGISTER").all()
        assert len(logs) >= 1

    def test_audit_log_created_on_login(self, client, sample_user, admin_headers, db):
        from app.models import AuditLog

        client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})

        logs = AuditLog.query.filter_by(action="AUTH_LOGIN_SUCCESS").all()
        assert len(logs) >= 1

    def test_audit_log_created_on_failed_login_without_password(self, client, sample_user, db):
        from app.models import AuditLog

        client.post("/api/auth/login", json={"username": "testuser", "password": "wrong-password"})

        log = AuditLog.query.filter_by(action="AUTH_LOGIN_FAILED").first()
        assert log is not None
        assert "wrong-password" not in (log.detail or "")
        assert json.loads(log.detail)["reason"] == "invalid_credentials"

    def test_audit_logs_filter_and_metrics(self, client, db, sample_user, admin_headers):
        from app.models import AuditLog

        now = datetime.now(UTC)
        rows = [
            AuditLog(
                user_id=sample_user.id,
                action="AUTH_LOGIN_FAILED",
                resource_type="user",
                resource_id=str(sample_user.id),
                detail=json.dumps({"username": sample_user.username, "result": "failed", "reason": "invalid_credentials"}),
                created_at=now - timedelta(hours=1),
            ),
            AuditLog(
                user_id=sample_user.id,
                action="TASK_CREATE",
                resource_type="task",
                resource_id="88",
                detail=json.dumps({"task_id": 88, "task_type": "SCA", "result": "created"}),
                created_at=now - timedelta(hours=2),
            ),
            AuditLog(
                user_id=sample_user.id,
                action="REPORT_EXPORT_PDF",
                resource_type="task",
                resource_id="88",
                detail=json.dumps({"task_id": 88, "task_type": "SCA", "format": "pdf", "result": "success"}),
                created_at=now - timedelta(days=2),
            ),
        ]
        db.session.add_all(rows)
        db.session.commit()

        response = client.get(
            "/api/audit-logs?action=TASK_CREATE&resource_id=88&result=created",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["pagination"]["total"] == 1
        assert data["items"][0]["action_label"] == "创建扫描任务"
        assert data["items"][0]["result"] == "created"
        assert data["summary"]["login_failed_count"] == 1
        assert data["summary"]["task_create_count"] == 1
        assert data["charts"]["by_action"]["TASK_CREATE"] == 1
        assert len(data["charts"]["by_hour_24h"]) == 24
