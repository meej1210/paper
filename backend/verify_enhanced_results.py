import time
from pathlib import Path

from app import create_app
from app.models import TaskType, User, SastIssue, DastIssue
from app.services.dast_service import run_dast_scan
from app.services.sast_service import run_bandit_scan
from app.services.task_service import create_task

app = create_app()

with app.app_context():
    user = User.query.first()
    if not user:
        raise RuntimeError("No users found in database. Register a user first.")

    sample_dir = Path(app.config["UPLOAD_DIR"])
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_path = sample_dir / f"verify_enhanced_{int(time.time())}.py"
    sample_path.write_text("import subprocess\nsubprocess.Popen('ls', shell=True)\n", encoding="utf-8")

    sast_task = create_task(
        user_id=user.id,
        task_type=TaskType.SAST,
        task_name="verify-enhanced-sast",
        description="enhanced sast verification",
        target_path=str(sample_path),
    )
    run_bandit_scan(sast_task)

    dast_task = create_task(
        user_id=user.id,
        task_type=TaskType.DAST,
        task_name="verify-enhanced-dast",
        description="enhanced dast verification",
        target_url="http://127.0.0.1:3000",
        timeout_seconds=60,
    )
    run_dast_scan(dast_task)

    print({
        "sast_task": sast_task.to_dict(),
        "sast_result": sast_task.sast_result.to_dict() if sast_task.sast_result else None,
        "sast_issue_count": SastIssue.query.filter_by(task_id=sast_task.id).count(),
        "dast_task": dast_task.to_dict(),
        "dast_result": dast_task.dast_result.to_dict() if dast_task.dast_result else None,
        "dast_issue_count": DastIssue.query.filter_by(task_id=dast_task.id).count(),
    })
