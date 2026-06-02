import json
from pathlib import Path

import pytest

from scripts.run_dast_lab_samples import build_summary_rows, load_targets


def test_load_targets_requires_name_and_url(tmp_path):
    targets_path = tmp_path / "targets.json"
    targets_path.write_text(json.dumps([{"name": "juice-shop"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="name and url"):
        load_targets(targets_path)


def test_build_summary_rows_extracts_dast_metrics():
    payload = {
        "data": {
            "task": {"id": 7, "status": "SUCCESS", "duration_ms": 1234},
            "result": {
                "crawled_pages": 12,
                "issue_count": 3,
                "severity_distribution": {"HIGH": 1, "MEDIUM": 1, "LOW": 1},
                "type_distribution": {"SQL Injection": 2, "XSS": 1},
            },
        }
    }

    rows = build_summary_rows([
        {
            "target": {"name": "dvwa", "url": "http://127.0.0.1:3001"},
            "round": 1,
            "payload": payload,
            "report_path": Path("tmp/dast-lab-samples/dast_report_7.json"),
        }
    ])

    assert rows == [
        {
            "target": "dvwa",
            "url": "http://127.0.0.1:3001",
            "round": 1,
            "task_id": 7,
            "status": "SUCCESS",
            "duration_ms": 1234,
            "crawled_pages": 12,
            "issue_count": 3,
            "critical": 0,
            "high": 1,
            "medium": 1,
            "low": 1,
            "top_types": "SQL Injection=2; XSS=1",
            "report": "tmp\\dast-lab-samples\\dast_report_7.json",
        }
    ]
