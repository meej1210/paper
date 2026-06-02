import io

from app.models import Task, TaskStatus, TaskType, User
from tests.conftest import _auth_headers as auth_headers


def _create_sca_task(client, user_id, filename="requirements.txt", content="flask==3.0.0\n", **extra_form):
    data = {"file": (io.BytesIO(content.encode()), filename), **extra_form}
    return client.post("/api/sca/tasks", data=data, headers=auth_headers(user_id), content_type="multipart/form-data")


def test_create_sca_task_requires_auth(client):
    data = {"file": (io.BytesIO(b"flask==3.0.0\n"), "requirements.txt")}
    response = client.post("/api/sca/tasks", data=data, content_type="multipart/form-data")

    assert response.status_code == 401


def test_create_sca_task_accepts_requirements_txt(client, sample_user, monkeypatch):
    monkeypatch.setattr("app.api.sca.execute_sca_task", lambda task_id: None)

    response = _create_sca_task(client, sample_user.id, task_name="Dependency audit")

    assert response.status_code == 201
    task = response.get_json()["data"]["task"]
    assert task["task_type"] == "SCA"
    assert task["task_name"] == "Dependency audit"
    assert task["status"] == "PENDING"
    assert task["target_name"].endswith("requirements.txt")


def test_create_sca_task_rejects_unsupported_file(client, sample_user):
    response = _create_sca_task(client, sample_user.id, filename="package.json", content='{"dependencies":{}}')

    assert response.status_code == 400
    assert response.get_json()["errors"]["file"] == "unsupported extension"


def test_create_sca_task_accepts_zip(client, sample_user, monkeypatch):
    monkeypatch.setattr("app.api.sca.execute_sca_task", lambda task_id: None)
    response = _create_sca_task(client, sample_user.id, filename="project.zip", content="not a real zip yet")

    assert response.status_code == 201
    assert response.get_json()["data"]["task"]["task_type"] == "SCA"


def test_get_sca_task_owner_scope(client, sample_user, db):
    from app.utils.security import hash_password

    other = User(username="scaother", email="scaother@example.com", password_hash=hash_password("password123"))
    db.session.add(other)
    db.session.commit()
    task = Task(user_id=other.id, task_type=TaskType.SCA, status=TaskStatus.SUCCESS, target_path="/tmp/requirements.txt")
    db.session.add(task)
    db.session.commit()

    response = client.get(f"/api/sca/tasks/{task.id}", headers=auth_headers(sample_user.id))

    assert response.status_code == 404
