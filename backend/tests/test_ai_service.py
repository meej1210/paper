import json

import pytest

from app.models import ScaIssue, Task, TaskStatus, TaskType
from app.services.ai_service import _build_prompt, _call_deepseek, get_issue_insight
from app.utils.exceptions import ApiError


def test_sast_prompt_requires_concise_pain_point_output():
    prompt = _build_prompt(
        TaskType.SAST.value,
        {
            "file": "app.py",
            "line_number": 12,
            "issue_text": "Use of hard-coded password string.",
        },
    )

    assert "用户痛点" in prompt
    assert "每个字段只写 1 句" in prompt
    assert "每句不超过 45 个汉字" in prompt
    assert "先说当前证据暴露的直接问题" in prompt
    assert "不要输出背景科普" in prompt


def test_dast_prompt_requires_path_parameter_specific_output():
    prompt = _build_prompt(
        TaskType.DAST.value,
        {
            "method": "GET",
            "path": "/search",
            "parameter": "q",
            "info": "Reflected XSS",
        },
    )

    assert "用户痛点" in prompt
    assert "当前路径/方法/参数" in prompt
    assert "不要输出背景科普" in prompt
    assert "下一步动作" in prompt


def test_call_deepseek_uses_configured_openrouter_endpoint_and_model(app, monkeypatch):
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_API_BASE"] = "http://example.test/openrouter/v1"
    app.config["AI_MODEL"] = "deepseek-v4-pro"

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "meaning": "直接问题",
                                        "impact": "实际影响",
                                        "fix": "修复动作",
                                        "verify": "验证方式",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(http_request.header_items())
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("app.services.ai_service.request.urlopen", fake_urlopen)

    result = _call_deepseek("prompt")

    assert captured["url"] == "http://example.test/openrouter/v1/chat/completions"
    assert captured["body"]["model"] == "deepseek-v4-pro"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert result["model_name"] == "deepseek-v4-pro"


def test_get_issue_insight_finds_sca_issue(app, db, sample_user, monkeypatch):
    task = Task(user_id=sample_user.id, task_type=TaskType.SCA, status=TaskStatus.SUCCESS)
    db.session.add(task)
    db.session.commit()
    issue = ScaIssue(
        task_id=task.id,
        package_name="django",
        installed_version="2.2",
        vulnerability_id="PYSEC-2021-9",
        aliases='["CVE-2021-3281"]',
        fix_versions='["2.2.18"]',
        description="Directory traversal via archive extraction.",
        severity="HIGH",
    )
    db.session.add(issue)
    db.session.commit()

    monkeypatch.setattr(
        "app.services.ai_service._call_deepseek",
        lambda prompt: {
            "meaning": "Django 2.2 has a known archive traversal issue.",
            "impact": "An attacker may write files outside the expected path.",
            "fix": "Upgrade Django to 2.2.18 or a later fixed version.",
            "verify": "Run SCA again after upgrading the dependency.",
            "model_name": "test-model",
        },
    )

    result = get_issue_insight(task, issue.id)

    assert result["issue_id"] == issue.id
    assert result["cached"] is False
    assert result["insight"]["task_type"] == "SCA"
    assert result["insight"]["meaning"] == "Django 2.2 has a known archive traversal issue."


def test_get_issue_insight_rejects_unknown_sca_issue(app, db, sample_user):
    task = Task(user_id=sample_user.id, task_type=TaskType.SCA, status=TaskStatus.SUCCESS)
    db.session.add(task)
    db.session.commit()

    with pytest.raises(ApiError) as exc_info:
        get_issue_insight(task, 999)

    assert exc_info.value.status_code == 404
