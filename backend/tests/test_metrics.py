from datetime import UTC, datetime, timedelta

from app.models import Task, TaskStatus, TaskType, User
from app.utils.security import hash_password
from tests.conftest import _auth_headers as auth_headers


def _task(user_id, task_type, status, *, duration_ms=None, created_at=None):
    if not hasattr(_task, "_counter"):
        _task._counter = {}
    _task._counter[user_id] = _task._counter.get(user_id, 0) + 1
    return Task(
        user_task_no=_task._counter[user_id],
        user_id=user_id,
        task_type=task_type,
        status=status,
        duration_ms=duration_ms,
        created_at=created_at or datetime.now(UTC),
    )


def test_task_summary_user_scope(client, sample_user, db):
    other = User(username="metrics-other", email="metrics-other@example.com", password_hash=hash_password("password123"))
    db.session.add(other)
    db.session.flush()
    db.session.add(_task(sample_user.id, TaskType.SAST, TaskStatus.SUCCESS, duration_ms=1000))
    db.session.add(_task(other.id, TaskType.DAST, TaskStatus.FAILED, duration_ms=2000))
    db.session.commit()

    response = client.get("/api/metrics/task-summary", headers=auth_headers(sample_user.id))

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["scope"] == "user"
    assert data["totals"] == 1
    assert data["by_type"] == {"SAST": 1, "DAST": 0, "SCA": 0}


def test_task_summary_admin_all_scope(client, admin_user, sample_user, db):
    db.session.add(_task(sample_user.id, TaskType.SAST, TaskStatus.SUCCESS, duration_ms=1000))
    db.session.add(_task(admin_user.id, TaskType.SCA, TaskStatus.PENDING))
    db.session.commit()

    response = client.get("/api/metrics/task-summary?scope=all", headers=auth_headers(admin_user.id))

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["scope"] == "all"
    assert data["totals"] == 2
    assert data["pending_count"] == 1


def test_task_summary_status_distribution(client, sample_user, db):
    db.session.add(_task(sample_user.id, TaskType.SAST, TaskStatus.SUCCESS, duration_ms=1000))
    db.session.add(_task(sample_user.id, TaskType.DAST, TaskStatus.FAILED, duration_ms=3000))
    db.session.add(_task(sample_user.id, TaskType.SCA, TaskStatus.RUNNING))
    db.session.commit()

    response = client.get("/api/metrics/task-summary", headers=auth_headers(sample_user.id))

    data = response.get_json()["data"]
    assert data["by_status"]["SUCCESS"] == 1
    assert data["by_status"]["FAILED"] == 1
    assert data["by_status"]["RUNNING"] == 1
    assert data["running_count"] == 1
    assert data["failed_count"] == 1
    assert data["average_duration_ms"] == 2000


def test_task_summary_recent_24h_window(client, sample_user, db):
    old = datetime.now(UTC) - timedelta(hours=30)
    db.session.add(_task(sample_user.id, TaskType.SAST, TaskStatus.SUCCESS, created_at=old))
    db.session.add(_task(sample_user.id, TaskType.SCA, TaskStatus.SUCCESS))
    db.session.commit()

    response = client.get("/api/metrics/task-summary", headers=auth_headers(sample_user.id))

    assert response.get_json()["data"]["recent_24h_count"] == 1
