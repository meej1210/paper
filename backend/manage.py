from flask.cli import FlaskGroup

from app import create_app
from app.extensions import db
from app.models import AiIssueInsight, AuditLog, DastIssue, DastResult, SastIssue, SastResult, Task, User

app = create_app()
cli = FlaskGroup(create_app=create_app)


@app.shell_context_processor
def shell_context():
    return {
        "db": db,
        "User": User,
        "Task": Task,
        "AuditLog": AuditLog,
        "SastResult": SastResult,
        "SastIssue": SastIssue,
        "DastResult": DastResult,
        "DastIssue": DastIssue,
        "AiIssueInsight": AiIssueInsight,
    }


if __name__ == "__main__":
    cli()
