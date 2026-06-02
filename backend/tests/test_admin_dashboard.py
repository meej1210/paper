import json
from datetime import UTC, datetime

from app.models import AuditLog, DastIssue, DastResult, SastIssue, ScaIssue, Task, TaskStatus, TaskType, User, UserRole
from app.utils.security import hash_password
from tests.conftest import _auth_headers as auth_headers


def test_admin_dashboard_requires_admin(client, sample_user):
    response = client.get("/api/admin/dashboard", headers=auth_headers(sample_user.id))
    assert response.status_code == 403


def test_admin_dashboard_returns_task_totals(client, admin_user, sample_user, db):
    db.session.add(Task(user_id=sample_user.id, user_task_no=1, task_type=TaskType.SAST, status=TaskStatus.SUCCESS))
    db.session.add(Task(user_id=sample_user.id, user_task_no=2, task_type=TaskType.SCA, status=TaskStatus.FAILED))
    db.session.commit()

    response = client.get("/api/admin/dashboard", headers=auth_headers(admin_user.id))

    assert response.status_code == 200
    totals = response.get_json()["data"]["task_totals"]
    assert totals["total"] == 2
    assert totals["by_type"]["SAST"] == 1
    assert totals["by_status"]["FAILED"] == 1


def test_admin_dashboard_includes_recent_audit_logs(client, admin_user, db):
    db.session.add(AuditLog(user_id=admin_user.id, action="TASK_CREATE", resource_type="task", resource_id="1", detail="created"))
    db.session.commit()

    response = client.get("/api/admin/dashboard", headers=auth_headers(admin_user.id))

    logs = response.get_json()["data"]["recent_audit_logs"]
    assert logs[0]["action"] == "TASK_CREATE"


def test_admin_dashboard_includes_dast_authorization_targets(client, admin_user, sample_user, db):
    task = Task(
        user_id=sample_user.id,
        user_task_no=1,
        task_type=TaskType.DAST,
        status=TaskStatus.SUCCESS,
        target_url="http://127.0.0.1:3000",
        authorization_confirmed=True,
        target_host="127.0.0.1",
        target_ip="127.0.0.1",
        target_policy="localhost",
    )
    db.session.add(task)
    db.session.commit()

    response = client.get("/api/admin/dashboard", headers=auth_headers(admin_user.id))

    target = response.get_json()["data"]["dast_targets"][0]
    assert target["target_host"] == "127.0.0.1"
    assert target["authorization_confirmed"] is True
    assert target["target_policy"] == "localhost"


def test_admin_dashboard_returns_risk_summary(client, admin_user, sample_user, db):
    sast_task = Task(user_id=sample_user.id, user_task_no=1, task_type=TaskType.SAST, status=TaskStatus.SUCCESS)
    dast_task = Task(user_id=sample_user.id, user_task_no=2, task_type=TaskType.DAST, status=TaskStatus.SUCCESS, target_url="http://127.0.0.1:3000")
    sca_task = Task(user_id=sample_user.id, user_task_no=3, task_type=TaskType.SCA, status=TaskStatus.SUCCESS)
    db.session.add_all([sast_task, dast_task, sca_task])
    db.session.flush()
    db.session.add(SastIssue(task_id=sast_task.id, issue_severity="HIGH"))
    db.session.add(DastResult(task_id=dast_task.id, target_url="http://127.0.0.1:3000", severity_distribution=json.dumps({"HIGH": 2})))
    db.session.add(DastIssue(task_id=dast_task.id, level="MEDIUM"))
    db.session.add(ScaIssue(task_id=sca_task.id, package_name="django", vulnerability_id="PYSEC-1", fix_versions=json.dumps(["4.2.1"])))
    db.session.commit()

    response = client.get("/api/admin/dashboard", headers=auth_headers(admin_user.id))

    risk = response.get_json()["data"]["risk_summary"]
    assert risk["sast"]["HIGH"] == 1
    assert risk["dast"]["HIGH"] == 2
    assert risk["sca"]["vulnerability_count"] == 1
    assert risk["sca"]["fixable_count"] == 1


def test_admin_tasks_requires_admin(client, sample_user):
    response = client.get("/api/admin/tasks", headers=auth_headers(sample_user.id))

    assert response.status_code == 403


def test_admin_tasks_lists_all_users_with_report_links(client, admin_user, sample_user, db):
    other_user = User(username="other", email="other@example.com", password_hash=hash_password("pass123"), role=UserRole.USER)
    db.session.add(other_user)
    db.session.flush()
    db.session.add_all(
        [
            Task(
                user_id=sample_user.id,
                user_task_no=1,
                task_type=TaskType.SAST,
                task_name="sample sast",
                status=TaskStatus.SUCCESS,
                report_path="reports/sast.html",
            ),
            Task(
                user_id=other_user.id,
                user_task_no=1,
                task_type=TaskType.DAST,
                task_name="other dast",
                status=TaskStatus.FAILED,
                target_url="http://127.0.0.1:3000",
            ),
        ]
    )
    db.session.commit()

    response = client.get("/api/admin/tasks?page=1&page_size=20", headers=auth_headers(admin_user.id))

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["pagination"]["total"] == 2
    users = {item["user"]["email"] for item in data["items"]}
    assert users == {sample_user.email, "other@example.com"}
    report_item = next(item for item in data["items"] if item["task_name"] == "sample sast")
    assert report_item["report_available"] is True
    assert report_item["report_route"] == f"/tasks/{report_item['id']}?type=SAST&from=admin"


def test_admin_tasks_supports_user_and_type_filters(client, admin_user, sample_user, db):
    other_user = User(username="filter-other", email="filter-other@example.com", password_hash=hash_password("pass123"), role=UserRole.USER)
    db.session.add(other_user)
    db.session.flush()
    db.session.add_all(
        [
            Task(user_id=sample_user.id, user_task_no=1, task_type=TaskType.SCA, task_name="sample sca", status=TaskStatus.SUCCESS),
            Task(user_id=other_user.id, user_task_no=1, task_type=TaskType.SAST, task_name="other sast", status=TaskStatus.SUCCESS),
        ]
    )
    db.session.commit()

    response = client.get(
        f"/api/admin/tasks?user_id={sample_user.id}&task_type=SCA",
        headers=auth_headers(admin_user.id),
    )

    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["user"]["id"] == sample_user.id
    assert items[0]["task_type"] == "SCA"


def test_admin_can_open_other_users_sast_detail(client, admin_user, sample_user, db):
    task = Task(user_id=sample_user.id, user_task_no=1, task_type=TaskType.SAST, task_name="other user report", status=TaskStatus.SUCCESS)
    db.session.add(task)
    db.session.commit()

    response = client.get(f"/api/sast/tasks/{task.id}", headers=auth_headers(admin_user.id))

    assert response.status_code == 200
    assert response.get_json()["data"]["task"]["id"] == task.id
